import gzip
import json
import csv
import re
import os
from collections import defaultdict
from datetime import datetime, timedelta
import io

import celery
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction, IntegrityError

from capdb.models import VolumeXML, PageXML, CaseXML, VolumeMetadata
from capdb.storages import ingest_storage, inventory_storage, redis_client, redis_ingest_client as r
from scripts.helpers import resolve_namespace, parse_xml

logger = get_task_logger(__name__)
info = logger.info

"""
This script updates the capstone inventory based on an inventory report from s3

The reports consist of a json manifest file which is a map to 10k-key gzipped
CSV files. The CSV files are not seemingly meaningfully named, and they're all
dumped in the data directory of the report, so you really need the manifest to
make sense of the report.

harvard-cap-inventory/harvard-ftl-shared/PrimarySharedInventoryReport:

-- 2017-07-12T21-03Z
---- manifest.checksum
---- manifest.json
--2017-07-13T18-03Z
---- manifest.checksum
---- manifest.json
-- 2017-[etc.]
-- data
---- 0063018d-cc37-4f64-a00e-db4607a478aa.csv.gz
---- 009c84a9-0d15-4858-8594-272a5b1606b6.csv.gz
---- 00[etc.].csv.gz

Since many volumes are broken up between two inventory files, and some are
old versions that should not be uploaded at all, we use redis to make a database
of keys to organize the inventory report data before it's actually ingested. 
A "queue" in the code is a redis unordered set.

The overall flow of the script is outlined in sync_s3_data().
"""


### entry point ###

@celery.shared_task
def sync_s3_data(full_sync=False):
    """
        Sync XML data from S3.

        If full_sync is false, only sync files updated since the last sync (if any), or else within the last week.
    """

    # pre-run setup
    wipe_redis_db()

    # We have two rounds of fanning out jobs to celery workers, because we first have to gather the listing of files
    # for each volume, and then process each valid volume that is discovered.

    # Round One:
    #   - Find the latest manifest.json and get list of inventory files to process.
    #   - Call read_inventory_file() as a celery task for each inventory file. For each file:
    #      - Add name of each unique volume folder to the "volumes" queue.
    #      - Add list of volume files to "volume:<volume_folder>" queue.
    #   - Return when all celery tasks are complete.
    read_inventory_files(full_sync)

    # Round Two:
    #   - Filter down "volumes" queue to most recent copy of each volume.
    #   - Call ingest_volume() as a celery task for each volume. For each volume:
    #       - Ingest volume XML, case XML, and alto XML, if not already in database.
    #       - If we are adding/updating volume XML, check that METS inventory is valid.
    ingest_volumes(full_sync)

    # post-run teardown
    report_errors()
    write_last_sync()
    wipe_redis_db()


### processing steps ###

def wipe_redis_db():
    """
        Clear out the redis ingest database.
        This database is defined by settings.REDIS_INGEST_DB; it's distinct from our default redis DB.
    """
    r.flushdb()


def read_inventory_files(full_sync):
    """
        Get list of inventory files and start a celery task for each file, returning when all tasks are complete.
    """

    # find the newest inventory report directory, telling us which manifest file to read:
    subdirs = sorted(inventory_storage.iter_files(), reverse=True)
    last_subdir = next(subdir for subdir in subdirs if not subdir.endswith('data'))
    manifest_path = os.path.join(last_subdir, "manifest.json")

    # read manifest file:
    manifest = json.loads(inventory_storage.contents(manifest_path))
    inventory_files = (trim_manifest_key(inventory_file['key']) for inventory_file in manifest['files'])
    field_names = manifest['fileSchema'].split(", ")

    # get earliest last-modified date we're interested in:
    minimum_date_str = None if full_sync else get_last_sync().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    # process each inventory file:
    run_tasks(read_inventory_file, inventory_files, extra_args=(field_names, minimum_date_str, full_sync))


@celery.shared_task
def read_inventory_file(inventory_file, field_names, minimum_date_str, full_sync):
    """
        Process a single inventory file and add contents to redis queues.
    """
    info("Processing manifest file: %s" % inventory_file)

    volume_regex = re.compile(r'from_vendor/([A-Za-z0-9]+_redacted[^/]*)(/.+)')
    files_grouped_by_volume = defaultdict(list)

    # read inventory file, grouping relevant files by volume name
    for file_entry in get_inventory_file_entries(inventory_file, field_names):
        # filter out old files
        if not full_sync and file_entry['LastModifiedDate'] < minimum_date_str:
            continue

        # extract volume_folder name and file_name relative to volume folder
        m = volume_regex.search(file_entry['Key'])
        if m:
            volume_folder, file_name = m.groups()

            # filter out irrelevant files
            if file_name.endswith('md5') or file_name.endswith('/'):
                continue

            # store tuple of (file_name, etag) grouped by volume_folder
            files_grouped_by_volume[volume_folder].append([file_name, file_entry['ETag']])

    # Add group of files for each volume to volume:<volume_folder> queue.
    # Note that all files for a volume are added as a single queue item, tab and newline delimited.
    for volume_folder, files in files_grouped_by_volume.items():
        files_str = "\n".join("\t".join(line) for line in files)
        r.sadd("volumes", volume_folder)
        r.sadd("volume:" + volume_folder, files_str)


def ingest_volumes(full_sync):
    """
        Start a celery task to ingest each valid volume folder, returning when all tasks are complete.
    """

    # Get list of volume folders in reverse alphabetical order, with duplicates removed.
    # (List will contain duplicates because volumes can appear in more than one inventory file.)
    volume_folders = sorted(set(spop_all("volumes")), reverse=True)

    # Add the first occurrence of each volume to filtered_volume_folders.
    # First occurrence in reverse-alphabetical order will be most recently-created volume,
    # which supersedes earlier versions.
    previous_barcode = None
    filtered_volume_folders = []
    for volume_folder in volume_folders:
        barcode = volume_folder.split(b'_', 1)[0]
        if barcode == previous_barcode:
            # delete redis queues for duplicate volumes
            r.delete('volume:' + volume_folder)
        else:
            previous_barcode = barcode
            filtered_volume_folders.append(volume_folder)

    # process each unique volume
    run_tasks(ingest_volume, filtered_volume_folders, extra_args=(full_sync,))


@celery.shared_task
@transaction.atomic
def ingest_volume(volume_folder, full_sync):
    """
        Celery task to ingest a single volume folder.
    """
    info("Processing volume: %s" % volume_folder)
    volume_folder = volume_folder.decode()

    # Get all entries from volume:<volume_folder> queue, splitting tab-delimited strings back into tuples:
    s3_items = [line.split("\t") for files_str in spop_all('volume:' + volume_folder) for line in
                files_str.decode().split("\n")]

    # sort s3 items by file type:
    s3_items_by_type = {'alto': [], 'jp2': [], 'tiff': [], 'casemets': [], 'volmets': [], 'md5': []}
    for file_name, etag in s3_items:
        s3_key = volume_folder + file_name
        file_type = get_file_type(s3_key)
        if file_type:
            s3_items_by_type[file_type].append((s3_key, etag))

    # set up variables for ingest:
    volume_barcode = volume_folder.split('_', 1)[0]
    volmets_path, volmets_md5 = s3_items_by_type['volmets'][0]
    alto_barcode_to_case_map = defaultdict(list)

    try:
        with transaction.atomic():
            # get or create VolumeXML object from VolumeMetadata entry for this barcode:
            volume_metadata = VolumeMetadata.objects.select_related('volume_xml').defer('volume_xml__orig_xml').get(
                barcode=volume_barcode)
            try:
                volume = volume_metadata.volume_xml
            except VolumeXML.DoesNotExist:
                volume = VolumeXML(metadata=volume_metadata)

            # If not forced full_sync, s3_key is already set, and same md5, skip this volume:
            if not full_sync and volmets_path == volume.s3_key and volume.md5 == volmets_md5:
                info("Skipping %s, already ingested." % volume_folder)
                return False

            # update volume xml
            if volume.md5 != volmets_md5:
                volume.orig_xml = ingest_storage.contents(volmets_path)

                # make sure that file listing in volmets matches s3 files; otherwise record error for this volume and return
                volmets_valid = validate_volmets(volume.orig_xml, s3_items_by_type, path_prefix=volume_folder + '/')
                if not volmets_valid:
                    store_error("nonmatching_files", volume_folder)
                    return False

            volume.s3_key = volmets_path
            if volume.tracker.changed():
                volume.save()

            ### import cases

            # make sure existing cases have metadata (this check can possibly be removed after first run)
            for case in volume.case_xmls.filter(metadata_id=None):
                case.create_or_update_metadata()

            # create or update each case
            existing_cases = {c.metadata.case_id: c for c in
                              volume.case_xmls.select_related('metadata').defer('orig_xml')}
            for case_s3_key, case_md5 in s3_items_by_type['casemets']:
                case_barcode = volume_barcode + "_" + case_s3_key.split('.xml', 1)[0].rsplit('_', 1)[-1]

                case = existing_cases.pop(case_barcode, None)

                # handle existing case
                if case:
                    case.s3_key = case_s3_key
                    if case.md5 != case_md5:
                        case.orig_xml = ingest_storage.contents(case_s3_key)

                # handle new case
                else:
                    case = CaseXML(
                        volume=volume,
                        s3_key=case_s3_key,
                        orig_xml=ingest_storage.contents(case_s3_key),
                    )

                if case.tracker.changed():
                    xml_changed = case.tracker.has_changed('orig_xml')

                    case.save()

                    if xml_changed:
                        # remove this when it gets called automatically by save()
                        case.create_or_update_metadata()

                        # store case-to-page matches
                        for alto_barcode in set(re.findall(r'file ID="alto_(\d{5}_[01])"', case.orig_xml)):
                            alto_barcode_to_case_map[volume_barcode + "_" + alto_barcode].append(case.id)

            ### import pages
            existing_pages = {p.barcode: p for p in volume.page_xmls.defer('orig_xml')}
            for page_s3_key, page_md5 in s3_items_by_type['alto']:
                alto_barcode = volume_barcode + "_" + page_s3_key.split('.xml', 1)[0].rsplit('_ALTO_', 1)[-1]

                page = existing_pages.pop(alto_barcode, None)

                # handle existing page
                if page:
                    page.s3_key = page_s3_key
                    if page.md5 != page_md5:
                        page.orig_xml = ingest_storage.contents(page_s3_key)

                # handle new page
                else:
                    page = PageXML(
                        volume=volume,
                        s3_key=page_s3_key,
                        barcode=alto_barcode,
                        orig_xml=ingest_storage.contents(page_s3_key),
                    )

                if page.tracker.changed():
                    page.save()

                # write case-to-page matches
                if alto_barcode_to_case_map[alto_barcode]:
                    page.cases.set(alto_barcode_to_case_map[alto_barcode])

            for spare_case in existing_cases:
                store_error("spare_case", volume_folder, spare_case.pk)

            for spare_page in existing_pages:
                store_error("spare_page", volume_folder, spare_page.pk)

    except IntegrityError as e:
        store_error("integrity_error", volume_folder, e)


def report_errors():
    if r.scard("errors"):
        info("Errors during ingest:")
        for item in spop_all("errors"):
            info(item)


def write_last_sync():
    redis_client.set("last_sync", str(datetime.now()))


### helpers ###

def store_error(*args):
    r.sadd("errors", json.dumps([str(arg) for arg in args]))


def run_tasks(task, args, extra_args=tuple()):
    """ Run given celery task for each arg in args. Run tasks in parallel, but wait to return until all tasks are done. """
    celery.group(task.s(arg, *extra_args) for arg in args)().get()


def spop_all(key):
    while r.scard(key) > 0:
        yield r.spop(key)


def validate_volmets(volume_file, s3_items_by_type, path_prefix):
    """Confirm that all paths and hashes in volmets match files in S3. """
    parsed = parse_xml(volume_file)

    for file_type in ('jp2', 'tiff', 'alto', 'casemets'):
        volmets_files = set(
            (
                path_prefix + i.children('mets|FLocat').attr(resolve_namespace('xlink|href')),
                i.attr('CHECKSUM')
            ) for i in parsed('mets|fileGrp[USE="%s"] mets|file' % file_type).items()
        )
        if set(s3_items_by_type[file_type]) != volmets_files:
            return False
    return True


def get_last_sync():
    """
        Return last time we completed a sync, defaulting to one week.

        Uses "redis_client" instead of "r" because the "r" redis database gets wiped at the start and end of ingest.
    """
    if redis_client.exists("last_sync"):
        return datetime.strptime(redis_client.get("last_sync").decode(), '%Y-%m-%d %H:%M:%S.%f')
    else:
        return datetime.now() - timedelta(days=7)


def get_inventory_file_entries(key, field_names):
    """ Returns iterator over files listed in inventory report manifest, parsed as CSV """
    with inventory_storage.open(key, mode='rb') as f:
        with gzip.GzipFile(fileobj=f) as g:
            for line in csv.DictReader(io.TextIOWrapper(g), fieldnames=field_names, delimiter=',', quotechar='"'):
                yield line


def trim_manifest_key(key):
    """
        Keys in manifest.json include the full path in the S3 bin.
        Our inventory_storage object is relative to a subdir, so we have to strip the beginning of the key.
    """
    return key[len(settings.INVENTORY['manifest_path_prefix']):]


def trim_csv_key(key):
    """
        Keys in inventory CSV files include the full path in the S3 bin.
        Our ingest_storage object is relative to a subdir, so we have to strip the beginning of the key.
    """
    return key[len(settings.INVENTORY['csv_path_prefix']):]


def get_file_type(path):
    """ Get file type for path. """
    if path.endswith('.jp2'):
        return 'jp2'
    if path.endswith('.tif'):
        return 'tiff'
    if '/alto/' in path:
        if path.endswith('.xml'):
            return 'alto'
        return None
    if '/casemets/' in path:
        if path.endswith('.xml'):
            return 'casemets'
        return None
    if path.endswith('METS.md5'):
        return 'md5'
    if path.endswith('METS.xml'):
        return 'volmets'
    return None