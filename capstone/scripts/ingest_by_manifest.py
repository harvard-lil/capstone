import gzip
import json
import csv
import re
import itertools
import os
from collections import defaultdict

from datetime import datetime, timedelta
from multiprocessing import Pool

import redis
import boto3
import botocore

from django.conf import settings
from django.db import transaction, IntegrityError
from capdb.models import VolumeXML, PageXML, CaseXML


SHARED_BUCKET_NAME = settings.SHARED_BUCKET_NAME
INVENTORY_BUCKET_NAME = settings.INVENTORY['inventory_bucket_name']
SHARED_REPORT_DIRECTORY = settings.INVENTORY['inventory_directory']
_last_sync = None

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

I store the last DB sync in redis and use that to determine from which date 
the sync should run. Alternately, you can just run the whole thing with 
complete_data_sync. This could be a incur a non-negligable expense on our 
AWS bill. 


"""

def sync_recent_data():
    inventory_build_pool()
    trim_old_versions()
    inventory_ingest_pool()
    write_last_sync()

def complete_data_sync():
    global _last_sync
    _last_sync = datetime(1970, 1, 1)

    inventory_build_pool()
    trim_old_versions()
    inventory_ingest_pool()
    write_last_sync()

def inventory_build_pool():
    manifest_texts = [json.loads(get_s3_file(INVENTORY_BUCKET_NAME, key))['files'] for key in get_fresh_manifests()]
    pool = Pool(64)
    pool.map_async(process_recent_manifest_data, [file['key'] for file in itertools.chain(*manifest_texts)])
    pool.close()
    pool.join()

def inventory_ingest_pool():
    pool = Pool(64)
    r = redis.Redis( host='localhost', port=6379)
    while r.scard("new_volumes") > 0:
        pool.map_async(readqueue, [ r.spop("new_volumes") ])
    pool.close()
    pool.join()


def trim_old_versions():
    """Gets all of the versions in the unsorted volume queue, checks the version string, only passes on the highest version string"""
    r = redis.Redis( host='localhost', port=6379)
    while r.scard("unsorted_new_volumes") > 0:
        unsorted_volume = r.spop("unsorted_new_volumes") 
        vol_dict = json.loads(unsorted_volume.decode("utf-8"))
        
        all_versions = [volume for volume in r.smembers("unsorted_new_volumes")
            if json.loads(volume.decode("utf-8"))['barcode'] == vol_dict['barcode']] + [unsorted_volume]

        highest_version_string = max([json.loads(version)['version_string'] for version in all_versions
            if json.loads(version.decode("utf-8"))['barcode'] == vol_dict['barcode']])
        
        for version in all_versions:
            version_dict = json.loads(version.decode("utf-8"))
            if unsorted_volume != version_dict:
                r.srem("unsorted_new_volumes", version)
            if version_dict['version_string'] == highest_version_string:
                r.sadd("new_volumes", version)
            else:
                r.sadd("superceded", version)

def readqueue(vol_entry_bytestring):
    """Ingests what's in the new_volumes queue"""
    r = redis.Redis( host='localhost', port=6379)

    vol_entry = json.loads(vol_entry_bytestring.decode("utf-8"))
    file_types = ['casemets', 'jp2', 'tif', 'alto', 'vol']
    queues = {}
    
    
    for file_type in file_types:
        queues[file_type] = "{}_{}_{}_inventory".format(vol_entry['barcode'], file_type, vol_entry['version_string'])
        if file_type == 'vol':
            continue
        mets_queue = "{}_{}_{}_mets".format(vol_entry['barcode'], file_type, vol_entry['version_string'])

        if set(r.smembers(queues[file_type])) != set(r.smembers(mets_queue)):
            r.sadd("wrong_number_of_files", vol_entry_bytestring)
            return False

    process_volume(vol_entry, queues)
    
def process_volume(vol_entry, queues):
    """This ingests the volume into the capstone database"""
    r = redis.Redis( host='localhost', port=6379)
    bucket, volmets_path = json.loads(r.spop(queues['vol']).decode("utf-8"))
    alto_barcode_to_case_map = defaultdict(list)
    
    try:
        with transaction.atomic():
            volume = VolumeXML.objects.filter(barcode=vol_entry['barcode']).first()
            if volume:
                if is_same_complete_volume(volume, vol_entry, bucket, queues, vol_entry['barcode']):
                    return False
                else:
                    volume.delete()
            volume = VolumeXML(orig_xml=get_s3_file(bucket, volmets_path), barcode=vol_entry['barcode'], s3_key=volmets_path)
            volume.save()
            
            while r.scard(queues['casemets']) > 0:
                case_entry = json.loads(r.spop(queues['casemets']))
                case_s3_key = case_entry[1]
                case_bucket = case_entry[0]
                
                case = CaseXML.objects.filter(case_id=vol_entry['barcode']).first()

                case_barcode = vol_entry['barcode'] + "_" + case_s3_key.split('.xml', 1)[0].rsplit('_', 1)[-1]
                case = CaseXML(orig_xml=get_s3_file(case_bucket, case_s3_key), volume=volume, case_id=case_barcode)
                case.save()
                case.update_case_metadata()

                # store case-to-page matches
                for alto_barcode in set(re.findall(r'file ID="alto_(\d{5}_[01])"', case.orig_xml)):
                    alto_barcode_to_case_map[vol_entry['barcode'] + "_" + alto_barcode].append(case.id)

            # save altos
            while r.scard(queues['alto']) > 0:
                page_entry = json.loads(r.spop(queues['alto']))
                page_s3_key = page_entry[1]
                page_bucket = page_entry[0]

                alto_barcode = vol_entry['barcode'] + "_" + page_s3_key.split('.xml', 1)[0].rsplit('_ALTO_', 1)[-1]
                page = PageXML(orig_xml=get_s3_file(page_bucket, page_s3_key), volume=volume, barcode=alto_barcode)
                page.save()

                # write case-to-page matches
                if alto_barcode_to_case_map[alto_barcode]:
                    page.cases.set(alto_barcode_to_case_map[alto_barcode])

    except IntegrityError as e:
        print("Integrity Error... {} probably already exists: {}".format(volmets_path, e))



def process_recent_manifest_data(list_key):
    """This goes through the files in the inventory report and puts them into
       queues. It makes queues for the alto files entries, and the inventory
       report key entries. They're organized by bar code, version string, and
       file type
    """
    file_list = get_file_list(INVENTORY_BUCKET_NAME, list_key)
    r = redis.Redis( host='localhost', port=6379)
    for file_entry in file_list:
        file_key = file_entry[1]
        if (
                len(file_entry) == 0 or
                not file_entry[1].startswith('from_vendor') or
                file_entry[1].endswith('md5') or
                datetime.strptime(file_entry[3], '%Y-%m-%dT%H:%M:%S.%fZ') < check_last_sync() or
                file_entry[1].endswith('/')
            ):
            continue
        
        barcode = file_entry[1].split("/")[1].split('_')[0]
        bucket = file_entry[0]
        file_key = file_entry[1]

        version_match = re.match(r'from_vendor/[A-Za-z0-9]+_redacted_?([0-9_\.]+)/', file_key)
        version_string = version_match[1] if version_match is not None else "0000_original"

        #a length of less than 4 means it's a volume-level file
        if len(file_key.split("/")) < 4:
            mets_files = extract_file_dict(bucket, file_key)
            for queue_type in mets_files:
                queue_name = "{}_{}_{}_mets".format(barcode, queue_type, version_string)
                [r.sadd(queue_name, json.dumps([bucket, "{}/{}".format(os.path.dirname(file_key), f)])) for f in mets_files[queue_type]]
            
            json_add = json.dumps({
                "barcode": barcode, 
                "timestamp": str(datetime.now(tz=None)), 
                "version_string": version_string})
            r.sadd("unsorted_new_volumes", json_add)
            r.sadd("{}_vol_{}_inventory".format(barcode, version_string), json.dumps([bucket, file_key]))
        else:
            split_key = re.match(r'from_vendor/[A-Za-z0-9]+_redacted([0-9_\.]+)?/((images|alto|casemets)/[A-Za-z0-9_]+\.(jp2|xml|tif))', file_key)
            if split_key[4] == 'jp2' or split_key[4] == 'tif':
                tag_file(bucket, file_key, split_key[4])
                queue_name = "{}_{}_{}_inventory".format(barcode, split_key[4], version_string)
            else:
                queue_name = "{}_{}_{}_inventory".format(barcode, split_key[3], version_string)
            r.sadd(queue_name, json.dumps([bucket, file_key]))

def extract_file_dict(bucket, key):
    """Gets the files assocated with the volume from the mets"""
    volume_file=get_s3_file(bucket, key)
    files = re.findall(r'<FLocat LOCTYPE="URL" xlink:href="(([A-Za-z]+)/(([A-Za-z_0-9]+).(jp2|xml|tif)))"/>', volume_file)
    file_dict = defaultdict()

    file_dict['jp2'] = [ file[0] for file in files if file[4] == 'jp2' ]
    file_dict['tif'] = [ file[0] for file in files if file[4] == 'tif' ]
    file_dict['alto'] = [ file[0] for file in files if file[1] == 'alto' ]
    file_dict['casemets'] = [ file[0] for file in files if file[1] == 'casemets' ]
    return file_dict

def is_same_complete_volume(volume, vol_entry, bucket, queues, barcode):
    """This checks to see if the volume in the bucket is the same volume that's in the DB"""
    r = redis.Redis( host='localhost', port=6379)
    existing_case_keys = set(CaseXML.objects.filter(volume=volume).values_list('s3_key', flat=True))
    existing_page_keys = set(PageXML.objects.filter(volume=volume).values_list('s3_key', flat=True))

    if ( existing_case_keys == set([entry[0] for entry in r.smembers(queues['casemets'])]) and
            existing_page_keys == set([entry[0] for entry in r.smembers(queues['alto'])])
        ):
        return True

    elif not volume_has_multi_s3_versions(bucket, vol_entry['barcode']):
        existing_case_ids = set(CaseXML.objects.filter(volume=volume).values_list('case_id', flat=True))
        existing_page_ids = set(PageXML.objects.filter(volume=volume).values_list('barcode', flat=True))
        for alto_file in r.smembers(queues['alto']):
            alto_id = "{}_{}".format(barcode, re.search(r'ALTO_([0-9]+_[0-9])\.xml', alto_file.decode('utf-8'))[1])
            if alto_id not in existing_page_ids:
                return False
            else:
                existing_page_ids.remove(alto_id)
        for case_file in r.smembers(queues['casemets']):
            case_id = "{}_{}".format(barcode, re.search(r'CASEMETS_([0-9]+)\.xml', case_file.decode('utf-8'))[1])
            if case_id not in existing_case_ids:
                return False
            else:
                existing_case_ids.remove(case_id) 
        if len(existing_case_ids) + len(existing_page_ids) > 0:
            return False
    else:
        return False

    return True


def check_last_sync():
    """ This function gets called a LOT. Stores value in a global and returns that if it's already been checked
        if no last sync value is found in redis, it defaults to a value of one week.
    """
    global _last_sync
    if _last_sync is None:
        r = redis.Redis(host='localhost', port=6379)
        if r.exists("last_sync"):
            _last_sync = datetime.strptime(r.get("last_sync").decode(), '%Y-%m-%d %H:%M:%S.%f')
        else:
            _last_sync = datetime.now() - timedelta(days=7)
    return _last_sync

def write_last_sync():
    r = redis.Redis( host='localhost', port=6379)
    r.set("last_sync", str(datetime.now()))

def get_fresh_manifests():
    """ gets the most recent inventory report manifest files"""
    s3 = boto3.client('s3')
    results = s3.list_objects_v2(
        Bucket=INVENTORY_BUCKET_NAME,
        Delimiter='/',
        Prefix="{}/{}/".format(SHARED_BUCKET_NAME, SHARED_REPORT_DIRECTORY)
    )

    # takes directories in results['CommonPrefixes'], filters out 'data/' & dirs older than the last sync, adds manifest.json filename
    return [
        "{}manifest.json".format(prefix['Prefix'])
        for prefix in results['CommonPrefixes'] 
        if not prefix['Prefix'].endswith('data/') and
        datetime.strptime(re.split('/', prefix['Prefix'])[2], '%Y-%m-%dT%H-%MZ') > check_last_sync()
    ]

def tag_file(bucket, key, file_type):
    """ This tags image file with their file type, so we can send jp2s to IA"""
    s3 = boto3.client('s3')
    results = s3.put_object_tagging(
        Bucket=bucket,
        Key=key,
        Tagging={
            'TagSet': [
                {
                    'Key': 'file_type',
                    'Value': file_type
                }
            ]
        }
    )
    # boto3 should return 'versionID': (version id) if successful, this will return True or False
    return 'VersionId' in results

def get_s3_file(bucket, key):
    s3 = boto3.client('s3')
    try:
        result = s3.get_object(Bucket=bucket, Key=key)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
    return result['Body'].read().decode('utf-8', errors="ignore")

def get_file_list(bucket, key):
    """Returns a list of inventory files listed in the inventory report manifest"""
    s3 = boto3.client('s3')
    try:
        result = s3.get_object(Bucket=bucket, Key=key)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
    return list(csv.reader(gzip.decompress(result['Body'].read()).decode().split('\n'), delimiter=',', quotechar='"'))

def volume_has_multi_s3_versions(bucket, barcode):
    """Checks if there are multiple versions from innodata"""
    s3_client = boto3.client('s3')
    results = s3_client.list_objects_v2(
        Bucket=bucket,
        Delimiter='/',
        Prefix="from_vendor/{}".format(barcode)
    )
    return True if results['KeyCount'] > 1 else False


