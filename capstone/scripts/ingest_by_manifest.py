import gzip
import json
import csv
import re
import os
from collections import defaultdict
from datetime import datetime, timedelta
import io

import celery
from celery import chord
from celery.exceptions import ChordError
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import IntegrityError, DatabaseError
from django.utils.encoding import force_str

from capdb.models import VolumeXML, PageXML, CaseXML, VolumeMetadata
from capdb.storages import ingest_storage, inventory_storage, redis_client, redis_ingest_client as r
from scripts.helpers import resolve_namespace, parse_xml
from scripts.process_ingested_xml import build_case_page_join_table

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

        If full_sync is false, only sync files where the VolumeXML with that md5 has not already been successfully ingested.
    """

    # pre-run setup
    wipe_redis_db()

    # Round One:
    #   - Find the latest manifest.json and get list of inventory files to process.
    #   - Call read_inventory_file() as a celery task for each inventory file. For each file:
    #      - Add name of each unique volume folder to the "volumes" queue.
    #      - Add list of volume files to "volume:<volume_folder>" queue.
    #   - Call sync_s3_data_step_two when all celery tasks are complete.
    read_inventory_files(full_sync)

@celery.shared_task
def sync_s3_data_step_two(full_sync=False):
    # Round Two:
    #   - Filter down "volumes" queue to most recent copy of each volume.
    #   - Call ingest_volume() as a celery task for each volume. For each volume:
    #       - Ingest volume XML, case XML, and alto XML, if not already in database.
    #       - If we are adding/updating volume XML, check that METS inventory is valid.
    #   - Call sync_s3_data_step_three when all celery tasks are complete.
    ingest_volumes(full_sync)

@celery.shared_task
def sync_s3_data_step_three():
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
    last_subdir = next(subdir for subdir in subdirs if subdir.endswith('Z'))  # subdir name should be a date; this skips 'hive' and 'data' folders
    manifest_path = os.path.join(last_subdir, "manifest.json")

    # read manifest file:
    manifest = json.loads(inventory_storage.contents(manifest_path))
    inventory_files = (trim_manifest_key(inventory_file['key']) for inventory_file in manifest['files'])
    field_names = manifest['fileSchema'].split(", ")

    # # get earliest last-modified date we're interested in:
    minimum_date_str = None # if full_sync else get_last_sync().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    # process each inventory file:
    chord(
        (read_inventory_file.s(i, field_names, minimum_date_str, full_sync) for i in inventory_files)
    )(sync_s3_data_step_two.si(full_sync))


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
        # # filter out old files
        # if not full_sync and file_entry['LastModifiedDate'] < minimum_date_str:
        #     continue

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

    # Fetch lists of VolumeMetadata entries from the database.
    already_ingested_db_volumes = set(VolumeMetadata.objects.filter(ingest_status='ingested').values_list('barcode', flat=True))
    not_ingested_db_volumes = set(VolumeMetadata.objects.filter(ingest_status__in=['to_ingest', 'error']).values_list('barcode', flat=True))
    all_db_volumes = already_ingested_db_volumes | not_ingested_db_volumes

    # Add the first occurrence of each volume to filtered_volume_folders.
    # First occurrence in reverse-alphabetical order will be most recently-created volume,
    # which supersedes earlier versions.
    previous_barcode = None
    filtered_volume_folders = []
    all_s3_barcodes = set()
    for volume_folder in volume_folders:
        volume_folder = force_str(volume_folder)
        barcode = volume_folder.split('_', 1)[0]

        # duplicate volume (earlier, superseded)
        if barcode == previous_barcode:
            # delete redis queues for duplicate
            r.delete('volume:' + volume_folder)

        # first occurrence of volume
        else:
            previous_barcode = barcode
            all_s3_barcodes.add(barcode)

            # skip already ingested volumes if not full_sync
            if not full_sync and barcode in already_ingested_db_volumes:
                continue

            # report error if S3 barcode isn't in VolumeMetadata db
            if barcode not in all_db_volumes:
                store_error("missing_volume_metadata", barcode)
                continue

            filtered_volume_folders.append(volume_folder)

    # Mark volumes that are in DB but not in S3.
    missing_from_s3 = all_db_volumes - all_s3_barcodes
    for barcode in missing_from_s3:
        VolumeMetadata.objects.filter(barcode=barcode).update(ingest_status='error', ingest_errors={"missing_from_s3": barcode})

    # process each unique volume
    try:
        chord(
            (ingest_volume.s(i) for i in filtered_volume_folders)
        )(sync_s3_data_step_three.si())
    except ChordError as e:
        # just log this -- detailed errors are collected in Redis and reported later
        logger.exception("Error ingesting at least one volume")

@celery.shared_task
def ingest_volume(volume_folder):
    """
        Celery task to ingest a single volume folder.
    """

    info("Processing volume: %s" % volume_folder)
    volume_folder = force_str(volume_folder)

    # Get all entries from volume:<volume_folder> queue, splitting tab-delimited strings back into tuples:
    s3_items = [line.split("\t") for files_str in spop_all('volume:' + volume_folder) for line in
                force_str(files_str).split("\n")]

    # sort s3 items by file type:
    s3_items_by_type = {'alto': [], 'jp2': [], 'tiff': [], 'casemets': [], 'volmets': [], 'md5': []}
    for file_name, etag in s3_items:
        s3_key = volume_folder + file_name
        file_type = get_file_type(s3_key)
        if file_type:
            s3_items_by_type[file_type].append((s3_key, etag))

    try:

        ### import volume

        # find VolumeMetadata entry for this barcode:
        volume_barcode = volume_folder.split('_', 1)[0]
        try:
            volume_metadata = VolumeMetadata.objects.select_related('volume_xml').defer('volume_xml__orig_xml').get(
                barcode=volume_barcode)
        except VolumeMetadata.DoesNotExist:
            # this shouldn't happen because we filter these out in ingest_volumes()
            return False

        volume_metadata.ingest_errors = None

        # check for missing volmets
        if not s3_items_by_type['volmets']:
            store_error("volmets_missing", volume_folder, volume_metadata=volume_metadata)
            return False

        # get or create VolumeXML object:
        try:
            volume = volume_metadata.volume_xml
        except VolumeXML.DoesNotExist:
            volume = VolumeXML(metadata=volume_metadata)

        # update volume xml
        volmets_path, volmets_md5 = s3_items_by_type['volmets'][0]
        if volume.md5 != volmets_md5:
            volume.orig_xml = ingest_storage.contents(volmets_path)

            # make sure that file listing in volmets matches s3 files; otherwise record error for this volume and return
            mismatched_files = validate_volmets(volume.orig_xml, s3_items_by_type, path_prefix=volume_folder + '/')
            if mismatched_files:
                store_error("nonmatching_files", {'s3_key': volume_folder, 'files': mismatched_files}, volume_metadata=volume_metadata)
                return False

        volume.s3_key = volmets_path
        if volume.tracker.changed():
            volume.save()

        ### import cases

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
                case.save(update_related=False)

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
                page.save(save_case=False, save_volume=False)

        ### cleanup

        # fill join table between PageXML and CaseXML
        build_case_page_join_table(volume.pk)

        # if errors, store to DB
        if existing_cases or existing_pages:
            if existing_cases:
                store_error("spare_db_cases", [e.pk for e in existing_cases.values()], volume_metadata=volume_metadata)
            if existing_pages:
                store_error("spare_db_pages", [e.pk for e in existing_pages.values()], volume_metadata=volume_metadata)

        # else mark volume as complete
        else:
            volume_metadata.ingest_status = "ingested"
            volume_metadata.save()

    except (IntegrityError, DatabaseError) as e:
        store_error("database_error", [volume_folder, str(e)], volume_metadata=volume_metadata)


def report_errors():
    if r.scard("errors"):
        info("Errors during ingest:")
        for item in spop_all("errors"):
            info(item)


def write_last_sync():
    redis_client.set("last_sync", str(datetime.now()))


### helpers ###

def store_error(error_code, error_data, volume_metadata=None):
    r.sadd("errors", json.dumps({'error_code': error_code, 'error_data': error_data, 'volume': volume_metadata.pk if volume_metadata else None}))
    if volume_metadata:
        if not volume_metadata.ingest_errors:
            volume_metadata.ingest_errors = {}
        volume_metadata.ingest_status = "error"
        volume_metadata.ingest_errors[error_code] = error_data
        volume_metadata.save()

def spop_all(key):
    while r.scard(key) > 0:
        yield r.spop(key)


def validate_volmets(volume_file, s3_items_by_type, path_prefix):
    """
        Confirm that all paths and hashes in volmets match files in S3.

        Returns 'None' if no errors detected, or else dict of files only in S3 and only in the METS file.
    """
    parsed = parse_xml(volume_file)

    only_in_mets = set()
    only_in_s3 = set()

    for file_type in ('jp2', 'tiff', 'alto', 'casemets'):
        volmets_files = set(
            (
                path_prefix + i.children('mets|FLocat').attr(resolve_namespace('xlink|href')),
                i.attr('CHECKSUM')
            ) for i in parsed('mets|fileGrp[USE="%s"] mets|file' % file_type).items()
        )
        if set(s3_items_by_type[file_type]) != volmets_files:
            only_in_mets |= volmets_files - s3_items_by_type[file_type]
            only_in_s3 |= s3_items_by_type[file_type] - volmets_files

    if only_in_mets or only_in_s3:
        return {
            'only_in_mets': list(only_in_mets),
            'only_in_s3': list(only_in_s3),
        }

    return None


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