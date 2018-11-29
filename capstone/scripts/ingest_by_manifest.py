import gzip
import json
import csv
import re
import os
from collections import defaultdict
import io

import celery
from celery import chord
from celery.result import allow_join_result
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import IntegrityError, DatabaseError
from django.utils.encoding import force_str

from capdb.models import VolumeXML, PageXML, CaseXML, VolumeMetadata
from capdb.storages import get_storage, ingest_storage, redis_ingest_client as r
from scripts.helpers import (resolve_namespace, parse_xml, volume_barcode_from_folder,
                             case_or_page_barcode_from_s3_key)
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
    if full_sync:
        raise Exception("""Full sync is not currently supported. We currently cannot distinguish between volumes that
            have been imported and edited in the database, and those that have been imported and had a second version
            uploaded to S3, so we will only import a volume from S3 a single time unless it is marked as
            import_status='pending' to trigger re-import.""")
    
    # pre-run setup
    wipe_redis_db()

    # Round One:
    #   - Find the latest manifest.json and get list of inventory files to process.
    #   - Call read_inventory_file() as a celery task for each inventory file. For each file:
    #      - Add name of each unique volume folder to the "volumes" queue.
    #      - Add list of volume files to "volume:<volume_folder>" queue.
    #   - Call sync_s3_data_step_two when all celery tasks are complete.

    # This "with" is required only because celery 4.2 falsely detects the following line as a problem when CELERY_TASK_ALWAYS_EAGER=True
    # See https://github.com/celery/celery/issues/4576
    with allow_join_result():

        read_inventory_files()(sync_s3_data_step_two.si(full_sync))

@celery.shared_task
def sync_s3_data_step_two(full_sync=False):
    # Round Two:
    #   - Filter down "volumes" queue to most recent copy of each volume.
    #   - Call ingest_volume_from_redis() as a celery task for each volume. For each volume:
    #       - Ingest volume XML, case XML, and alto XML, if not already in database.
    #       - If we are adding/updating volume XML, check that METS inventory is valid.
    #   - Call sync_s3_data_step_three when all celery tasks are complete.

    # This "with" is required only because celery 4.2 falsely detects the following line as a problem when CELERY_TASK_ALWAYS_EAGER=True
    # See https://github.com/celery/celery/issues/4576
    with allow_join_result():
        ingest_volumes(full_sync)(sync_s3_data_step_three.si())

@celery.shared_task
def sync_s3_data_step_three():
    # post-run teardown
    report_errors()
    wipe_redis_db()


### processing steps ###

def wipe_redis_db():
    """
        Clear out the redis ingest database.
        This database is defined by settings.REDIS_INGEST_DB; it's distinct from our default redis DB.
    """
    r.flushdb()


def read_inventory_files(storage_name='inventory_storage', manifest_path_prefix=settings.INVENTORY['manifest_path_prefix']):
    """
        Get list of inventory files and start a celery task for each file, returning when all tasks are complete.
    """

    inventory_storage = get_storage(storage_name)

    # find the newest inventory report directory, telling us which manifest file to read:
    subdirs = sorted(inventory_storage.iter_files(), reverse=True)
    last_subdir = next(subdir for subdir in subdirs if subdir.endswith('Z'))  # subdir name should be a date; this skips 'hive' and 'data' folders
    manifest_path = os.path.join(last_subdir, "manifest.json")

    # read manifest file:
    manifest = json.loads(inventory_storage.contents(manifest_path))

    # strip beginning of each key so keys work relative to inventory_storage's root dir:
    inventory_files = (inventory_file['key'][len(manifest_path_prefix):] for inventory_file in manifest['files'])

    field_names = manifest['fileSchema'].split(", ")

    # process each inventory file:
    return chord(
        (read_inventory_file.s(i, field_names, storage_name) for i in inventory_files)
    )


@celery.shared_task
def read_inventory_file(inventory_file, field_names, storage_name):
    """
        Process a single inventory file and add contents to redis queues.
    """
    info("Processing manifest file: %s" % inventory_file)

    inventory_storage = get_storage(storage_name)
    digitized_volume_regex = re.compile(r'from_vendor/([A-Za-z0-9]+_(?:un)?redacted[^/]*)(/.+)')
    born_digital_volume_regex = re.compile(r'from_vendor/([A-Za-z]+_\d+_(?:un)?redacted[^/]*)(/.+)')
    files_grouped_by_volume = defaultdict(list)

    # read inventory file, grouping relevant files by volume name
    for file_entry in get_inventory_file_entries(inventory_file, field_names, inventory_storage):
        # extract volume_folder name and file_name relative to volume folder
        dm = digitized_volume_regex.search(file_entry['Key'])
        bdm = born_digital_volume_regex.search(file_entry['Key'])

        if dm:
            m = dm
        elif bdm:
            m = bdm
        else:
            continue

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
    # Fetch lists of VolumeMetadata entries from the database.
    already_ingested_db_volumes = set(VolumeMetadata.objects.filter(ingest_status='ingested').values_list('barcode', flat=True))
    not_ingested_db_volumes = set(VolumeMetadata.objects.filter(ingest_status__in=['to_ingest', 'error']).values_list('barcode', flat=True))
    all_db_volumes = already_ingested_db_volumes | not_ingested_db_volumes

    # Add the first occurrence of each volume to filtered_volume_folders.
    filtered_volume_folders = []
    all_s3_barcodes = set()
    for volume_folder, barcode in get_unique_volumes_from_queue():
        all_s3_barcodes.add(barcode)

        # skip already ingested volumes if not full_sync
        if not full_sync and barcode in already_ingested_db_volumes:
            clear_redis_volume(volume_folder)
            continue

        filtered_volume_folders.append(volume_folder)

    # Mark volumes that are in DB but not in S3.
    missing_from_s3 = all_db_volumes - all_s3_barcodes
    for barcode in missing_from_s3:
        VolumeMetadata.objects.filter(barcode=barcode).update(ingest_status='error', ingest_errors={"missing_from_s3": barcode})

    # process each unique volume
    return chord(
        (ingest_volume_from_redis.s(i) for i in filtered_volume_folders)
    )

@celery.shared_task
def ingest_volume_from_redis(volume_folder):
    """
        Celery task to ingest a single volume folder.
    """
    info("Processing volume: %s" % volume_folder)
    volume_folder = force_str(volume_folder)
    s3_items_by_type = get_s3_items_by_type_from_queue(volume_folder)
    ingest_volume(volume_folder, s3_items_by_type)

@celery.shared_task
def ingest_volume_from_s3(volume_barcode):
    """
        Ingest a volume by requesting the S3 listing directly, instead of using inventory report.
    """
    # find latest volume folder based on barcode
    volume_folders = ingest_storage.iter_files(volume_barcode, partial_path=True)
    volume_folders = sorted(volume_folders, reverse=True)
    if not volume_folders:
        VolumeMetadata.objects.filter(barcode=volume_barcode).update(ingest_status='error', ingest_errors={"missing_from_s3": volume_barcode})
        return
    volume_folder = volume_folders[0]

    # fetch all items in folder
    s3_items = ((path.split(volume_folder, 1)[1], etag) for path, etag in ingest_storage.iter_files_recursive(volume_folder, with_md5=True))
    s3_items_by_type = sort_s3_items_by_type(s3_items, volume_folder)

    # ingest volume
    ingest_volume(volume_folder, s3_items_by_type)

def ingest_volume(volume_folder, s3_items_by_type):
    try:

        ### import volume
        # find VolumeMetadata entry for this barcode:
        volume_barcode = volume_barcode_from_folder(volume_folder)
        try:
            volume_metadata = VolumeMetadata.objects.select_related('volume_xml').defer('volume_xml__orig_xml').get(
                barcode=volume_barcode)
        except VolumeMetadata.DoesNotExist:
            volume_metadata = VolumeMetadata()

        needs_file_match_check = volume_metadata.ingest_errors and bool(volume_metadata.ingest_errors.get("nonmatching_files"))
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

        # check METS report of expected files vs actual files in S3
        if volume.md5 != volmets_md5 or needs_file_match_check:
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

            case = existing_cases.pop(case_or_page_barcode_from_s3_key(case_s3_key), None)

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
            alto_barcode = case_or_page_barcode_from_s3_key(page_s3_key)

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
        logger.error("Errors during ingest:")
        for item in spop_all("errors"):
            logger.error(item)


### helpers ###

def get_unique_volumes_from_queue():
    """
         Go through the "volumes" queue in redis in reverse alphabetical order.
         Yield the first occurrence of each volume by barcode, which will be the latest by date,
         and delete superseded volumes from redis.
    """
    volume_folders = sorted(set(spop_all("volumes")), reverse=True)

    previous_barcode = None
    for volume_folder in volume_folders:
        volume_folder = force_str(volume_folder)
        barcode = volume_barcode_from_folder(volume_folder)

        # duplicate volume (earlier, superseded)
        if barcode == previous_barcode:
            clear_redis_volume(volume_folder)

        # first occurrence of volume
        else:
            previous_barcode = barcode
            yield(volume_folder, barcode)

def get_s3_items_by_type_from_queue(volume_folder):
    """
        Load redis queue named "volume:<volume_folder>", and return dict of keys and md5s sorted by file type.
        Queue will contain items consisting of newline and tab-delimited lists of files.
        Returned value:

            {'alto': [[s3_key, md5], [s3_key, md5]], 'jp2': ..., 'tiff': ..., 'casemets': ..., 'volmets': ..., 'md5': ...}
    """
    # Get all entries from volume:<volume_folder> queue, splitting tab-delimited strings back into tuples:
    s3_items = [line.split("\t") for files_str in spop_all('volume:' + volume_folder) for line in
                force_str(files_str).split("\n")]
    return sort_s3_items_by_type(s3_items, volume_folder)

def sort_s3_items_by_type(s3_items, volume_folder):
    # sort s3 items by file type:
    s3_items_by_type = {'alto': [], 'jp2': [], 'tiff': [], 'casemets': [], 'volmets': [], 'md5': []}
    for file_name, etag in s3_items:
        s3_key = volume_folder + file_name
        file_type = get_file_type(s3_key)
        if file_type:
            s3_items_by_type[file_type].append((s3_key, etag))

    return s3_items_by_type

def store_error(error_code, error_data, volume_metadata=None):
    error_info = json.dumps({'error_code': error_code, 'error_data': error_data, 'volume': volume_metadata.pk if volume_metadata else None})
    logger.error(error_info)
    r.sadd("errors", error_info)
    if volume_metadata:
        if not volume_metadata.ingest_errors:
            volume_metadata.ingest_errors = {}
        volume_metadata.ingest_status = "error"
        volume_metadata.ingest_errors[error_code] = error_data
        volume_metadata.save()


def spop_all(key):
    while r.scard(key) > 0:
        yield r.spop(key)


def clear_redis_volume(volume_folder):
    r.delete('volume:' + volume_folder)

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
        s3_files = set(s3_items_by_type[file_type])
        if s3_files != volmets_files:
            only_in_mets |= volmets_files - s3_files
            only_in_s3 |= s3_files - volmets_files

    if only_in_mets or only_in_s3:
        return {
            'only_in_mets': list(only_in_mets),
            'only_in_s3': list(only_in_s3),
        }

    return None


def get_inventory_file_entries(key, field_names, inventory_storage):
    """ Returns iterator over files listed in inventory report manifest, parsed as CSV """
    with inventory_storage.open(key, mode='rb') as f:
        with gzip.GzipFile(fileobj=f) as g:
            for line in csv.DictReader(io.TextIOWrapper(g), fieldnames=field_names, delimiter=',', quotechar='"'):
                yield line


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


