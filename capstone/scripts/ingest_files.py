import os
import re
import time
from collections import defaultdict
from multiprocessing import Pool

from django.utils.module_loading import import_string

from django.conf import settings
from django.db import transaction, IntegrityError

from cap.models import Volume, Page, Case


### helpers ###

# Set up a Django abstract storage class for reading and writing to a file store -- could be either S3 or local files.
ingest_storage_class = import_string(settings.INGEST_STORAGE['class'])
ingest_storage = ingest_storage_class(**settings.INGEST_STORAGE.get('kwargs', {}))

def get_file_contents(path):
    print("Getting", path)
    with ingest_storage.open(path) as f:
        print("Got", f.read(100))
        f.seek(0)
        return f.read().decode('utf8')

### code ###

def ingest_volume(volume_path):
    print("Storing volume", volume_path)
    start_time = time.time()
    times = []

    # get volume ID
    vol_barcode = os.path.basename(volume_path.split('_redacted', 1)[0])
    alto_barcode_to_case_map = defaultdict(list)

    files = volume_files(volume_path)

    # save volume
    volmets_path = files['volume']

    try:
        with transaction.atomic():
            volume = Volume.objects.filter(barcode=vol_barcode).first()
            if volume:
                existing_case_ids = set(Case.objects.filter(volume=volume).values_list('barcode', flat=True))
                existing_page_ids = set(Page.objects.filter(volume=volume).values_list('barcode', flat=True))
            else:
                existing_case_ids = existing_page_ids = set()
                volume = Volume(orig_xml=get_file_contents(volmets_path), barcode=vol_barcode)
                volume.save()

            print("Processing Cases for " + volume_path)
            # save cases
            for xml_path in files['casemets']:
                case_barcode = vol_barcode + "_" + xml_path.split('.xml', 1)[0].rsplit('_', 1)[-1]
                if case_barcode not in existing_case_ids:
                    case = Case(orig_xml=get_file_contents(xml_path), volume=volume, barcode=case_barcode)
                    case.save()

                    # store case-to-page matches
                    for alto_barcode in set(re.findall(r'file ID="alto_(\d{5}_[01])"', case.orig_xml)):
                        alto_barcode_to_case_map[vol_barcode + "_" + alto_barcode].append(case.id)

            print("Processing Altos for " + volume_path)
            # save altos
            for xml_path in files['alto']:
                alto_barcode = vol_barcode + "_" + xml_path.split('.xml', 1)[0].rsplit('_ALTO_', 1)[-1]
                if alto_barcode not in existing_page_ids:
                    page = Page(orig_xml=get_file_contents(xml_path), volume=volume, barcode=alto_barcode)
                    page.save()

                    # write case-to-page matches
                    if alto_barcode_to_case_map[alto_barcode]:
                        page.cases.set(alto_barcode_to_case_map[alto_barcode])

            # Add relationship between pages and cases.
            # This could be done instead of the manual building of relationships up above,
            # if the sql was fast enough.
            # build_case_page_join_table(session, volume_id)

    except IntegrityError as e:
        print("Integrity Error... {} probably already exists: {}".format(volmets_path, e))

    # # write completed volume ID to file so we won't try to import it again if this is re-run
    # with open(ALREADY_READ_FILE_PATH, 'a') as out:
    #     out.write(vol_barcode+"\n")

    print("-- stored in %s: %s" % (time.time()-start_time, volume_path))

def ingest_volumes():
    """
    This function deploys the list of volumes to the ingest_volume function for processing
    """

    # # load list of volume IDs we've previously imported
    # if os.path.isfile(ALREADY_READ_FILE_PATH):
    #     with open(ALREADY_READ_FILE_PATH) as in_file:
    #         already_read = set(in_file.read().split())
    # else:
    #     already_read = []

    # find list of volumes to import from s3
    # build this as a list so we can pass it to the process Pool

    dirs = all_volumes()

    volume_paths = []
    for i, volume_path in enumerate(dirs):

        # skip dirs that are superseded by the following version
        base_name = volume_path.split('_redacted', 1)[0]
        if i < len(dirs)-1 and dirs[i+1].startswith(base_name):
            continue

        # # skip volumes read on previous run
        # vol_id = os.path.basename(volume_path.split('_redacted', 1)[0])
        # if vol_id in already_read:
        #     continue

        volume_paths.append(volume_path)

    # process volume directories in parallel processes
    pool = Pool(15)
    pool.map(ingest_volume, volume_paths)

    # keep this around in case we want to debug without using the process pool:
    #for i in volume_paths:
    #    ingest_volume(i)

def volume_files(volume_path):
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

    # check file paths for these patterns in order until we find one that matches
    regexes = [
        ('alto', re.compile(r'/alto/.*\.xml$')),
        ('images', re.compile(r'/images/.*\.(?:jp2|tif)$')),
        ('casemets', re.compile(r'/casemets/.*\.xml$')),
        ('volume', re.compile(r'\.xml$')),
        ('md5', re.compile(r'\.md5$')),
    ]

    print("Getting Volume Files for " + volume_path)
    for file_name in ingest_storage.iter_files(volume_path):
        for category, regex in regexes:
            if regex.search(file_name):
                files[category].append(file_name)
                break

    # unwrap lists that should only have one entry
    files['volume'] = files.get('volume', [None])[0]
    files['md5'] = files.get('md5', [None])[0]

    return files

def all_volumes():
    """ 
        Gets all of the volume "directories" in settings.INGEST_VOLUMES_PATH.
    """
    print("Getting Volume List")
    volumes = []
    for i, subdir in enumerate(ingest_storage.iter_subdirs()):
        volumes.append(subdir)
        if settings.INGEST_VOLUME_COUNT > 0 and i >= settings.INGEST_VOLUME_COUNT-1:
            return volumes
    return volumes