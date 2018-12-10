import logging
from celery import shared_task
from capdb.storages import transfer_storage
from scripts.helpers import storage_lookup, volume_barcode_from_folder

# logging
# disable boto3 info logging -- see https://github.com/boto/boto3/issues/521

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('nose').setLevel(logging.WARNING)
logging.getLogger('s3transfer').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
info = logger.info
info = print


@shared_task
def recursively_tag(storage_name, volume, dry_run, key='captar', value='ok'):
    """
    Tag for move to Glacier and delete from transfer bucket
    """
    dry_run = dry_run != 'false'

    info("%sTagging objects in %s" % ('DRY RUN: ' if dry_run else '', volume))
    # get all etags for objects matching this volume's barcode
    xfer_manifest = {}
    volume_barcode = volume_barcode_from_folder(volume)
    for folder in transfer_storage.iter_files(volume_barcode, partial_path=True):
        for (path, etag) in transfer_storage.iter_files_recursive(folder,
                                                                  with_md5=True):
            xfer_manifest[etag] = [path] + xfer_manifest.get(etag, [])
    # iterate through objects in this volume
    storage = storage_lookup[storage_name][0]
    for (object_path, object_etag) in storage.iter_files_recursive(path=volume,
                                                                   with_md5=True):
        # assume in the case of a dry run that tagging would have succeeded...
        tagged = dry_run or storage.tag_file(object_path, key, value)
        if dry_run:
            info("DRY RUN: tagging %s" % object_path)
        if tagged:
            if object_etag in xfer_manifest:
                for xfer_object in xfer_manifest[object_etag]:
                    deleted = dry_run or transfer_storage.delete_file(xfer_object)
                    if not deleted:
                        info("Failed to delete %s" % xfer_object)
                    if dry_run:
                        info("DRY RUN: deleting %s" % xfer_object)
        else:
            info("Failed to tag %s" % object_path)
