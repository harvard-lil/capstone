import gzip
import json
import csv
import re
import os
from collections import defaultdict
from datetime import datetime, timedelta
from multiprocessing import Pool
import io

from django import db
from django.conf import settings
from django.db import transaction, IntegrityError

from capdb.models import VolumeXML, PageXML, CaseXML, VolumeMetadata
from capdb.storages import ingest_storage, inventory_storage, redis_client as r

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

Since many volumes are broken up between two inventory files, and we're
not sure that all of the volumes will even be complete, because there are some
which innodata obviously did not upload the whole thing at once, I'm using
redis to make a database of keys to organize the inventory report data before
it's actualy ingested. What I refer to as a queue in the code is a redis 
unordered set.

The overall flow of the script goes like this:

1) inventory_build_pool()
 - ingests the inventory data from the bucket and puts it in redis.
 - new volumes are stored in the unsorted_new_volumes queue as they come in
 - different file types are stored in their own queues. Each one has a queue
   with files listed in METS, and one with files listed in the report

2) trim_old_versions()
 - makes sure we're only ingesting the most recent version listed in the report
 - moves files from the unsorted_new_volumes queue into the new_volumes queue

3) inventory_ingest_pool()
 - this step ingests the volumes/cases in the inventory report
 - uses new_volumes 
 - updates old volume versions with new versions
 - compares files in the ALTO with files in the ingest report to make sure we
 have everything

4) tag_jp2s()
 - tags all of the jp2 files for our process

5) cleanup_and_report()
 - deletes the queues that don't get popped
 - TODO this should also delete the inventory report files from s3
 - TODO this should email us a proper ingest report


The redis stuff is pretty straightforward. 
while r.scard("queue_name") > 0:
    r.spop("queue_name") 

I store the last DB sync in redis and use that to determine from which date 
the sync should run. Alternately, you can just run the whole thing with 
complete_data_sync. This could be a incur a non-negligable expense on our 
AWS bill. 

"""

ASYNC = True
_last_sync = None

### entry points ###

def sync_recent_data():
    empty_queues()
    inventory_build_pool()
    trim_old_versions()
    inventory_ingest_pool()
    tag_jp2s()
    cleanup_and_report()
    write_last_sync()

def complete_data_sync():
    global _last_sync
    _last_sync = datetime(1970, 1, 1)
    sync_recent_data()

### processing steps ###

def empty_queues():
    empty_set("nonmatching_files")
    empty_set("integrity_error")
    empty_set("tag_these_queues")
    empty_set("new_volumes")
    empty_set("unsorted_new_volumes")
    empty_set("spare_cases")

def inventory_build_pool():
    run_processes(process_recent_manifest_data, get_inventory_files_from_manifest(get_latest_manifest()))

def inventory_ingest_pool():
    run_processes(process_volume, (vol for vol in spop_all("new_volumes")))

def cleanup_and_report():
    for nonmatching_file in spop_all("nonmatching_files"):
        print(clean_queues(nonmatching_file))
    for integrity_error in spop_all("integrity_error"):
        print(clean_queues(integrity_error))
    for spare_cases in spop_all("integrity_error"):
        print("Spare Case: {}".format(spare_cases))

def tag_jp2s():
    for queue_to_tag in spop_all("tag_these_queues"):
        for jp2 in spop_all(queue_to_tag):
            tag_jp2(jp2)

def clean_queues(vol_entry_bytestring):
    """This ingests the volume into the capstone database"""
    queue_inventory = defaultdict(dict)
    queues = generate_queue_names(vol_entry_bytestring)
    for queue_type in queues:
        for file_type in queues[queue_type]:
            #we want to hang onto the jp2 queue for tagging
            if file_type == 'inventory' and queue_type == 'jp2':
                continue
            queue_inventory[queue_type][file_type] = "{} {}".format(queues[queue_type][file_type], r.scard(queues[queue_type][file_type]))
            r.delete(queues[queue_type][file_type])

    return queue_inventory

def trim_old_versions():
    """Gets all of the versions in the unsorted volume queue, checks the version string, only passes on the highest version string"""
    for unsorted_volume in spop_all("unsorted_new_volumes"):
        vol_dict = json.loads(unsorted_volume.decode("utf-8"))
        
        all_versions = [volume for volume in r.smembers("unsorted_new_volumes")
            if json.loads(volume.decode("utf-8"))['barcode'] == vol_dict['barcode']] + [unsorted_volume]

        highest_version_string = max([json.loads(version.decode("utf-8"))['version_string'] for version in all_versions
            if json.loads(version.decode("utf-8"))['barcode'] == vol_dict['barcode']])
        
        for version in all_versions:
            version_dict = json.loads(version.decode("utf-8"))
            if unsorted_volume != version_dict:
                r.srem("unsorted_new_volumes", version)

            if version_dict['version_string'] == highest_version_string:
                r.sadd("new_volumes", version)
            else:
                clean_queues(version)

def process_volume(vol_entry_bytestring):
    """This ingests the volume into the capstone database"""
    vol_entry = json.loads(vol_entry_bytestring.decode("utf-8"))
    queues = generate_queue_names(vol_entry_bytestring)
    global _last_sync

    # checks if keys/checksums in vol mets match keys/checksums in inventory
    for file_type in queues['mets']:
        if file_type == 'vol':
            continue
        if set(r.smembers(queues['inventory'][file_type])) != set(r.smembers(queues['mets'][file_type])):
            r.sadd("nonmatching_files", vol_entry_bytestring)
            return False

    bucket, volmets_path, volmets_md5 = json.loads(r.spop(queues['inventory']['vol']).decode("utf-8"))
    alto_barcode_to_case_map = defaultdict(list)
    
    try:
        with transaction.atomic():
            volume_metadata = VolumeMetadata.objects.get(barcode=vol_entry['barcode'])
            try:
                volume = volume_metadata.volume_xml
            except VolumeXML.DoesNotExist:
                volume = VolumeXML(metadata=volume_metadata)

            #same volmets path & same md5 & not forced full sync == same volume
            if (volmets_path == volume.s3_key and
                volume.md5 == volmets_md5 and
                _last_sync != datetime(1970, 1, 1)):
                return False

            if volume.md5 != volmets_md5:
                volume.orig_xml = ingest_storage.contents(volmets_path)
            volume.s3_key = volmets_path
            volume.save()

            existing_case_ids = set(volume.case_xmls.values_list('metadata__case_id', flat=True))
            for case_entry in spop_all(queues['inventory']['casemets']):
                case_entry = json.loads(case_entry.decode("utf-8"))
                case_s3_key = case_entry[1]
                case_md5 = case_entry[2]

                case_barcode = vol_entry['barcode'] + "_" + case_s3_key.split('.xml', 1)[0].rsplit('_', 1)[-1]
                if case_barcode in existing_case_ids:
                    existing_case_ids.remove(case_barcode)

                case, case_created = CaseXML.objects.get_or_create(volume=volume, metadata__case_id=case_barcode)
                if case.md5 != case_md5:
                    case.orig_xml = ingest_storage.contents(case_s3_key)
                case.s3_key = case_s3_key
                case.save()
                case.create_or_update_metadata()

                # store case-to-page matches
                for alto_barcode in set(re.findall(r'file ID="alto_(\d{5}_[01])"', str(case.orig_xml))):
                    alto_barcode_to_case_map[vol_entry['barcode'] + "_" + alto_barcode].append(case.id)

            existing_page_ids = set(volume.page_xmls.values_list('barcode', flat=True))
            # save altos
            for page_entry in spop_all(queues['inventory']['alto']):
                page_entry = json.loads(page_entry.decode("utf-8"))
                page_s3_key = page_entry[1]
                page_md5 = page_entry[2]

                alto_barcode = vol_entry['barcode'] + "_" + page_s3_key.split('.xml', 1)[0].rsplit('_ALTO_', 1)[-1]
                if alto_barcode in existing_page_ids:
                    existing_page_ids.remove(alto_barcode)

                page, page_created = PageXML.objects.get_or_create(volume=volume, barcode=alto_barcode)
                if page.md5 != page_md5:
                    page.orig_xml = ingest_storage.contents(page_s3_key)
                    page.s3_key = page_s3_key
                    page.save()

                    # write case-to-page matches
                    if alto_barcode_to_case_map[alto_barcode]:
                        page.cases.set(alto_barcode_to_case_map[alto_barcode])

            for spare_case in existing_case_ids:
                r.sadd("spare_cases_{}".format(vol_entry['barcode']), spare_case)

            for spare_page in existing_page_ids:
                r.sadd("spare_pages_{}".format(vol_entry['barcode']), spare_page)

    except IntegrityError as e:
        print("Integrity Error- {} : {}".format(volmets_path, e))
        r.sadd("integrity_error", vol_entry_bytestring)


def process_recent_manifest_data(list_key):
    """This goes through the files in the inventory report and puts them into
       queues. It makes queues for the alto files entries, and the inventory
       report key entries. They're organized by bar code, version string, and
       file type
    """

    version_regex = re.compile(r'[A-Za-z0-9]+_redacted_?([0-9_\.]+)/')
    key_regex = re.compile(r'[A-Za-z0-9]+_redacted([0-9_\.]+)?/((images|alto|casemets)/[A-Za-z0-9_]+\.(jp2|xml|tif))')
    for file_entry in read_inventory_file(list_key):
        if (
                len(file_entry) == 0 or
                not file_entry[1].startswith('from_vendor') or
                file_entry[1].endswith('md5') or
                datetime.strptime(file_entry[3], '%Y-%m-%dT%H:%M:%S.%fZ') < check_last_sync() or
                file_entry[1].endswith('/')
            ):
            continue

        md5 = file_entry[4]
        file_key = trim_csv_key(file_entry[1])
        barcode = file_key.split("/", 1)[0].split('_')[0]
        bucket = file_entry[0]

        version_match = version_regex.match(file_key)
        version_string = version_match.group(1) if version_match is not None else "0000_original"

        #a length of less than 3 means it's a volume-level file
        if len(file_key.split("/")) < 3:
            mets_files = extract_file_dict(bucket, file_key)
            for queue_type in mets_files:
                queue_name = "{}_{}_{}_mets".format(barcode, queue_type, version_string)
                [r.sadd(queue_name, json.dumps([bucket, "{}/{}".format(os.path.dirname(file_key), f[0]), f[1]])) for f in mets_files[queue_type]]
            json_add = json.dumps({
                "barcode": barcode, 
                "timestamp": str(datetime.now(tz=None)), 
                "version_string": version_string,
                "key": file_key,
                "md5": md5,
            })
            r.sadd("unsorted_new_volumes", json_add)
            r.sadd("{}_vol_{}_inventory".format(barcode, version_string), json.dumps([bucket, file_key, md5]))
        else:
            split_key = key_regex.match(file_key)
            if split_key.group(4) == 'jp2':
                queue_name = "{}_jp2_{}_inventory".format(barcode, version_string)
                r.sadd("tag_these_queues", queue_name)
            elif split_key.group(4) == 'tif':
                queue_name = "{}_tif_{}_inventory".format(barcode, version_string)
            else:
                queue_name = "{}_{}_{}_inventory".format(barcode, split_key.group(3), version_string)
            r.sadd(queue_name, json.dumps([bucket, file_key, md5]))

### helpers ###

def reopen_db_and_call(func, *args):
    # when running in subprocesses, Django database connections fight for the same socket, so re-open
    for connection_name in db.connections.databases:
        db.connections[connection_name].close()
        db.connections[connection_name].connect()
    return func(*args)

def run_processes(func, args):
    if ASYNC:
        pool = Pool(64)
        pool.starmap(reopen_db_and_call, ((func, arg) for arg in args))
        pool.close()
        pool.join()
    else:
        for arg in args:
            func(arg)

def spop_all(key):
    while r.scard(key) > 0:
        yield r.spop(key)

def empty_set(key):
    spop_all(key)

def extract_file_dict(bucket, key):
    """Gets the files assocated with the volume from the mets"""
    volume_file = ingest_storage.contents(key)

    #files = re.findall(r'<FLocat LOCTYPE="URL" xlink:href="(([A-Za-z]+)/(([A-Za-z_0-9]+).(jp2|xml|tif)))"/>', volume_file)
    files = re.findall(r'<file[A-Za-z0-9"=\s/_]+CHECKSUM="([a-zA-Z0-9]+)"[A-Za-z0-9"=\s]+>[\s\n]+<FLocat LOCTYPE="URL" xlink:href="(([A-Za-z]+)/(([A-Za-z_0-9]+).(jp2|xml|tif)))"/>[\s\n]+</file>', volume_file, re.MULTILINE)
    file_dict = defaultdict()

    file_dict['jp2'] = [ (file[1], file[0]) for file in files if file[5] == 'jp2' ]
    file_dict['tif'] = [ (file[1], file[0]) for file in files if file[5] == 'tif' ]
    file_dict['alto'] = [ (file[1], file[0]) for file in files if file[2] == 'alto' ]
    file_dict['casemets'] = [ (file[1], file[0]) for file in files if file[2] == 'casemets' ]
    return file_dict

def check_last_sync():
    """ This function gets called a LOT. Stores value in a global and returns that if it's already been checked
        if no last sync value is found in redis, it defaults to a value of one week.
    """
    global _last_sync
    if _last_sync is None:
        if r.exists("last_sync"):
            _last_sync = datetime.strptime(r.get("last_sync").decode(), '%Y-%m-%d %H:%M:%S.%f')
        else:
            _last_sync = datetime.now() - timedelta(days=7)
    return _last_sync

def write_last_sync():
    r.set("last_sync", str(datetime.now()))

def get_latest_manifest():
    """ get the most recent inventory report manifest file """
    subdirs = sorted(inventory_storage.iter_files(), reverse=True)
    last_subdir = next(subdir for subdir in subdirs if not subdir.endswith('data'))
    return os.path.join(last_subdir, "manifest.json")

def get_inventory_files_from_manifest(manifest_path):
    for inventory_file in json.loads(inventory_storage.contents(manifest_path))['files']:
        yield trim_manifest_key(inventory_file['key'])

def tag_jp2(file_entry):
    """ This tags image file with their file type, so we can send jp2s to IA"""
    file_dict = json.loads(file_entry.decode("utf-8"))
    key= file_dict[1]
    return ingest_storage.tag_file(key, 'file_type', 'jp2')

def read_inventory_file(key):
    """ Returns iterator over files listed in inventory report manifest """
    with inventory_storage.open(key, mode='rb') as f:
        with gzip.GzipFile(fileobj=f) as g:
            for line in csv.reader(io.TextIOWrapper(g), delimiter=',', quotechar='"'):
                yield line

def volume_has_multi_s3_versions(key):
    """Checks if there are multiple versions from innodata"""
    return '_redacted_' in key

def generate_queue_names(vol_entry_bytestring):
    vol_entry = json.loads(vol_entry_bytestring.decode("utf-8"))
    file_types = ['casemets', 'jp2', 'tif', 'alto', 'vol']
    queues = {}
    queues['inventory'] = {}
    queues['mets'] = {}
    
    for file_type in file_types:
        queues['inventory'][file_type] = "{}_{}_{}_inventory".format(vol_entry['barcode'], file_type, vol_entry['version_string'])
        if file_type == 'vol':
            continue
        queues['mets'][file_type] = "{}_{}_{}_mets".format(vol_entry['barcode'], file_type, vol_entry['version_string'])
    return queues

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