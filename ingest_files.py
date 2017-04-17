import time
from collections import defaultdict
from multiprocessing import Pool

import re

from sqlalchemy.sql import insert
from sqlalchemy.orm import sessionmaker
import os
from tqdm import tqdm
import boto3

from models import Volume, Page, Case, CasePage
from helpers import pg_connect

s3_bucket_name = "harvard-ftl-shared"
source_dir = "/ftldata/harvard-ftl-shared"


### helpers ###

def read_file(path):
    """
        Get contents of a local file by path.
    """
    with open(path) as in_file:
        return in_file.read()

def save_record(session, RecordClass, **kwargs):
    """
        Save a sqlalchemy record to the database.
    """
    record = RecordClass(**kwargs)
    session.add(record)
    return record

def get_s3_key(s3_client, key):
    """
        Get contents of an S3 object by key.
    """
    response = s3_client.get_object(Bucket=s3_bucket_name, Key=key)
    return response['Body'].read().decode('utf8')

def bm(times, label):
    """
        Helper function to record a benchmarking point -- handy for optimizing speed during dev.
    """
    times.append([time.time(), label])

def aggregate_bm(times):
    """
        Helper function to dump benchmarking points -- handy for optimizing speed during dev.
    """
    from pprint import pprint
    agg = defaultdict(lambda: defaultdict(int))
    for i, t in enumerate(times[1:]):
        agg[t[1]]['count'] += 1
        agg[t[1]]['total_time'] += t[0] - times[i-1][0]
    for a in agg.values():
        a['avg_time'] = a['total_time']/a['count']
    pprint(agg)


### code ###

def ingest_volume(volume_path):
    """
        This function runs in a multiprocessing pool, and only gets run once per process because it has a memory leak.
        So it has to build up everything it needs inside the function.
    """

    print("Storing volume", volume_path)
    start_time = time.time()
    times = []
    bm(times, "start")

    # get volume ID
    vol_barcode = os.path.basename(volume_path.split('_redacted', 1)[0])
    alto_barcode_to_case_map = defaultdict(list)

    # set up pg connection
    pg_con = pg_connect()
    Session = sessionmaker(bind=pg_con)
    session = Session()
    session.execute("SET LOCAL synchronous_commit TO OFF")

    # set up S3 connection
    s3_client = boto3.client('s3')


    bm(times, "setup")

    files = volume_files(s3_client, s3_bucket_name, vol_barcode)

    bm(times, "files loaded")

    # save volume
    volmets_path = files['volume']

    volume = session.query(Volume).filter(Volume.barcode == vol_barcode).first()
    if volume:
        bm(times, "getting caseids")
        existing_case_ids = set(barcode for barcode in session.query(Case.barcode).filter(Case.volume_id==volume.id))
        bm(times, "getting pageids")
        existing_page_ids = set(barcode for barcode in session.query(Page.barcode).filter(Page.volume_id==volume.id))
        bm(times, "done getting pageids")
    else:
        existing_case_ids = existing_page_ids = set()
        bm(times, "vol doesn't exist")
        orig_xml = get_s3_key(s3_client, volmets_path)
        bm(times, "read vol")
        volume = save_record(session, Volume, barcode=vol_barcode, orig_xml=orig_xml)
        session.flush()
        bm(times, "wrote vol")
        volume_id = volume.id


    # save cases
    for xml_path in files['casemets']:
        case_barcode = vol_barcode + "_" + xml_path.split('.xml', 1)[0].rsplit('_', 1)[-1]
        if case_barcode not in existing_case_ids:
            bm(times, "case doesn't exist")
            orig_xml = get_s3_key(s3_client, xml_path)
            bm(times, "read case")
            case = save_record(session, Case, volume_id=volume_id, barcode=case_barcode, orig_xml=orig_xml)
            session.flush()
            bm(times, "wrote case")

            # store case-to-page matches
            for alto_barcode in set(re.findall(r'file ID="alto_(\d{5}_[01])"', orig_xml)):
                alto_barcode_to_case_map[vol_barcode + "_" + alto_barcode].append(case.id)

    # save altos
    for xml_path in files['alto']:
        alto_barcode = vol_barcode + "_" + xml_path.split('.xml', 1)[0].rsplit('_ALTO_', 1)[-1]
        if alto_barcode not in existing_page_ids:
            bm(times, "page doesn't exist")
            #s3_key = xml_path.split(s3_bucket_name + '/', 1)[1]
            orig_xml = get_s3_key(s3_client, xml_path)
            bm(times, "read page")
            page = save_record(session, Page, volume_id=volume_id, barcode=alto_barcode, orig_xml=orig_xml)
            session.flush()
            bm(times, "wrote page")

            # write case-to-page matches
            if alto_barcode_to_case_map[alto_barcode]:
                insert_op = insert(CasePage).values(
                    [{"case_id": case_id, "page_id": page.id} for case_id in alto_barcode_to_case_map[alto_barcode]]
                )
                session.execute(insert_op)

    # Add relationship between pages and cases.
    # This could be done instead of the manual building of relationships up above, if the sql was fast enough.
    # build_case_page_join_table(session, volume_id)

    # commit session
    session.commit()

    bm(times, "committed")

    # write completed volume ID to file so we won't try to import it again if this is re-run
    with open('make_tables.py.stored', 'a') as out:
        out.write(vol_barcode+"\n")
    bm(times, "wrote id file")

    # benchmarking stuff
    # from pprint import pprint
    # pprint(times)
    # aggregate_bm(times)

    print("-- stored in %s: %s" % (time.time()-start_time, volume_path))

def ingest_volumes():

    # load list of volume IDs we've previously imported
    with open('make_tables.py.stored') as in_file:
        already_read = set(in_file.read().split())

    #set up s3 client
    s3_client = boto3.client('s3')

    # find list of volumes to import from s3
    # build this as a list so we can pass it to the process Pool
    dirs = all_volumes(s3_client, s3_bucket_name)


    volume_paths = []
    for i, volume_path in enumerate(tqdm(dirs)):


        ## skip dirs that are superseded by the following version
        base_name = volume_path.split('_redacted',1)[0]
        if i < len(dirs)-1 and dirs[i+1].startswith(base_name):
            continue

        # skip volumes read on previous run
        vol_id = os.path.basename(volume_path.split('_redacted', 1)[0])
        if vol_id in already_read:
            continue

        volume_paths.append(volume_path)



    # process volume directories in parallel processes
    #pool = Pool(15, maxtasksperchild=1)
    #pool.map(ingest_volume, volume_paths)

    # keep this around in case we want to debug without using the process pool:
    for i in volume_paths:
        ingest_volume(i)

def volume_files(s3_client, s3_bucket_name, barcode):
    """ This just gets all of the files in the volume directory, and puts them into
        a dictionary with a 'volume' array which has the volume mets and md5 files,
        'images' for the pics, 'alto' for the alto files, and 'casemets' for the 
        case files. I have one function to get all of the files rather than a generator
        to step through the results directly because there's a small enough number of files
        per volume to not be a 'huge' memory concern, and as far as wall clock time 
        goes, the request is the biggest drag, so having a different request for alto,
        casemets, and volume files would be much slower.
    """
    files = defaultdict(list)
    
    volume_path = 'from_vendor/' + barcode

    paginator = s3_client.get_paginator('list_objects')
    pages = paginator.paginate(Bucket=s3_bucket_name, Prefix=volume_path)

    for chunk in tqdm(pages):
        for item in chunk['Contents']:
            
            #this should tell us the name of the directory in the volume it's in. 
            file_type = item['Key'].split('/')[2]

            #if it's not one of these values, it's probably not in a directory
            if file_type == 'alto' or file_type == 'images' or file_type == 'casemets':
                files[file_type].append(item['Key'])
            elif item['Key'].endswith("xml"):
                    files['volume'] = item['Key']
            elif item['Key'].endswith("md5"):
                    files['md5'] = item['Key']
            else:
                print("Uncategorized Key: {}".format(item['Key']))

    return files

def all_volumes(s3_client, s3_bucket_name):
    """ Gets all of the volume "directories" in the specified bucket. For each entry with multiple
        versions, it only gives the most recent version.
    """
    
    volumes = []
    paginator = s3_client.get_paginator('list_objects')

    # get all of the volumes listed in from_vendor in the bucket
    for result in paginator.paginate(Bucket=s3_bucket_name, Prefix='from_vendor/', Delimiter='/'):
        for prefix in result.get('CommonPrefixes', []):
            dir = prefix.get('Prefix')
            volumes.append(dir)


    return volumes


if __name__ == "__main__":
    ingest_volumes()

