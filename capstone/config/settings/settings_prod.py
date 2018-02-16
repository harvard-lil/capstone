from .settings_base import *  # noqa

DEBUG = False

STORAGES = {
    'ingest_storage': {
        'class': 'capdb.storages.CapS3Storage',
        'kwargs': {
            'location': 'from_vendor',
            'bucket_name': 'harvard-ftl-shared',
        }
    },
    'inventory_storage': {
        'class': 'capdb.storages.CapS3Storage',
        'kwargs': {
            'location': 'harvard-ftl-shared/PrimarySharedInventoryReport',
            'bucket_name': 'harvard-cap-inventory',
        }
    }
}

INVENTORY = {
    # prefix to strip from paths in manifest.json
    'manifest_path_prefix': 'harvard-ftl-shared/PrimarySharedInventoryReport/',
    # prefix to strip from paths in .csv
    'csv_path_prefix': 'from_vendor/',
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

### API
API_DOCS_CASE_ID = '11301409' # Brown v. Board
