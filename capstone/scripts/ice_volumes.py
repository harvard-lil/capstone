import logging
from celery import shared_task
from capdb.storages import transfer_storage

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
def recursively_tag(storage, volume, key='captar', value='ok'):
    """
    Tag for move to Glacier
    """
    for (object_path, object_etag) in storage.iter_files_recursive(path=volume, with_md5=True):
        if storage.tag_file(object_path, key, value):
            info("tagged %s" % object_path)
            storage.delete_from_xfer(object_path, object_etag)
        else:
            info("failed to tag %s" % object_path)


@shared_task
def delete_from_xfer(object_path, object_etag, storage=transfer_storage):
    """
    Delete from xfer bucket when etags match
    """
    for (xfer_path, xfer_etag) in storage.iter_files_recursive(path=object_path, with_md5=True):
        if xfer_etag == object_etag:
            target = "%s from %s" % xfer_path, storage
            if storage.delete_file(xfer_path):
                info("deleted %s" % target)
            else:
                info("failed to delete %s" % target)
