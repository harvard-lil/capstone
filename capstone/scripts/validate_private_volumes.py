import json

import celery
from celery import chord
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils.encoding import force_str

from capdb.models import VolumeMetadata
from capdb.storages import private_ingest_storage
from scripts.helpers import volume_barcode_from_folder
from scripts.ingest_by_manifest import wipe_redis_db, read_inventory_files, get_unique_volumes_from_queue, \
    get_s3_items_by_type_from_queue, validate_volmets, report_errors, store_error

logger = get_task_logger(__name__)
info = logger.info


@celery.shared_task
def validate_private_volumes():
    wipe_redis_db()
    chord_result = read_inventory_files(
        storage_name='private_inventory_storage',
        manifest_path_prefix=settings.INVENTORY['private_manifest_path_prefix'])

    # run chord with callback for next step
    chord_result(validate_private_volumes_step_two.si())

@celery.shared_task
def validate_private_volumes_step_two():
    check_volumes()(validate_private_volumes_step_three.si())

@celery.shared_task
def validate_private_volumes_step_three():
    # post-run teardown
    report_errors()
    process_report()
    wipe_redis_db()

def check_volumes():
    """
        Start a celery task to ingest each valid volume folder, returning when all tasks are complete.
    """
    # process each unique volume
    unique_volumes = [volume_folder for volume_folder, barcode in get_unique_volumes_from_queue()]
    write_to_report("Checking volumes:\n%s\n\n" % json.dumps(unique_volumes))
    return chord(
        (check_volume.s(volume_folder) for volume_folder in unique_volumes)
    )

@celery.shared_task
def check_volume(volume_folder):

    info("Validating %s" % volume_folder)

    volume_folder = force_str(volume_folder)
    s3_items_by_type = get_s3_items_by_type_from_queue(volume_folder)

    # check for missing volmets
    if not s3_items_by_type['volmets']:
        store_error("volmets_missing", volume_folder)
        write_to_report("%s\t%s\n" % (volume_folder, "volments_missing"))
        return

    # check for mismatched files
    volmets_path, volmets_md5 = s3_items_by_type['volmets'][0]
    orig_xml = private_ingest_storage.contents(volmets_path)
    mismatched_files = validate_volmets(orig_xml, s3_items_by_type, path_prefix=volume_folder + '/')
    if mismatched_files:
        store_error("nonmatching_files", {'s3_key': volume_folder, 'files': mismatched_files})
        write_to_report("%s\t%s\t%s\n" % (volume_folder, "nonmatching_files", json.dumps(mismatched_files)))
        return

    write_to_report("%s\t%s\n" % (volume_folder, "ok"))

def write_to_report(message):
    with open("/tmp/validate_private_volumes_results.txt", "a") as out:
        out.write(message)

def process_report():
    with open("/tmp/validate_private_volumes_results.txt") as in_file:
        in_file.readline()
        expected_volumes = set(json.loads(in_file.readline()))
        in_file.readline()
        errors = {}
        processed_vols = set()
        for line in in_file:
            parts = line.strip().split("\t")
            volume_folder, error_code, details = parts[0], parts[1], parts[2:]
            expected_volumes.discard(volume_folder)
            processed_vols.add(volume_barcode_from_folder(volume_folder))
            if error_code == 'ok':
                continue
            error = {'error_code': error_code}
            if details:
                error['files'] = details[0]
            errors[volume_folder] = error

    for missed_volume in expected_volumes:
        errors[missed_volume] = {'error_code': 'in inventory report but not processed'}

    db_vols = VolumeMetadata.objects.exclude(ingest_status='skip').filter(xml_publication_year__gte=1923).values_list('pk', flat=True)
    missing_vols = set(db_vols) - processed_vols
    for missed_volume in missing_vols:
        errors[missed_volume] = {'error_code': 'in database but not in S3'}

    with open("/tmp/validate_private_volumes_report.txt", "w") as out:
        out.write(json.dumps(errors, indent=4))
