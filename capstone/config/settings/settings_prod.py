from .settings_base import *

DEBUG = False

INGEST_VOLUME_COUNT = 0  # unlimited
INGEST_STORAGE = {
    'class': 'cap.storages.CapS3Storage',
    'kwargs': {
        'location': 'from_vendor',
        'bucket_name': 'harvard-ftl-shared',
    }
}