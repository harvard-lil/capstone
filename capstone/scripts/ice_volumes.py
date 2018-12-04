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
def recursively_tag(storage_name, volume, key='captar', value='ok'):
    """
    Tag for move to Glacier and delete from transfer bucket
    """
    info("Tagging objects in %s" % volume)
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
        if storage.tag_file(object_path, key, value):
            if object_etag in xfer_manifest:
                for xfer_object in xfer_manifest[object_etag]:
                    transfer_storage.delete_file(xfer_object)
        else:
            info("Failed to tag %s" % object_path)
