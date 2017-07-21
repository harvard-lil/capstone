from .settings_base import *

DEBUG = False

INGEST_VOLUME_COUNT = 0  # unlimited
INGEST_STORAGE = {
    'class': 'capdb.storages.CapS3Storage',
    'kwargs': {
        'location': 'from_vendor',
        'bucket_name': 'harvard-ftl-shared',
    }
}

USE_TEST_TRACKING_TOOL_DB = False
DATABASES['tracking_tool'] = {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'ftl_tt',
    'USER': 'ftl_readonly',  # GRANT select ON ftl_tt.* TO 'ftl_readonly'@'%' identified by 'password' REQUIRE SSL;
    'PASSWORD': '',  # add to settings.py
    'HOST': '',      # add to settings.py
    'OPTIONS': {
        'ssl': {
            'ca': os.path.join(BASE_DIR, '../services/aws/rds-combined-ca-bundle.pem'),
        }
    }
}