from .settings_base import *  # noqa

DEBUG = False

STORAGES = {
    'ingest_storage': {
        'class': 'CapS3Storage',
        'kwargs': {
            'location': 'from_vendor',
            'bucket_name': 'harvard-ftl-shared',
        }
    },
    'private_ingest_storage': {
        'class': 'CapS3Storage',
        'kwargs': {
            'location': 'from_vendor',
            'bucket_name': 'harvard-ftl-private',
        }
    },
    'inventory_storage': {
        'class': 'CapS3Storage',
        'kwargs': {
            'location': 'harvard-ftl-shared/PrimarySharedInventoryReport',
            'bucket_name': 'harvard-cap-inventory',
        }
    },
    'private_inventory_storage': {
        'class': 'CapS3Storage',
        'kwargs': {
            'location': 'harvard-ftl-private/PrivateBucketInventory',
            'bucket_name': 'harvard-cap-inventory',
        }
    },
    'bulk_export_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'bulk-data'),
        },
    },
}

INVENTORY = {
    # prefix to strip from paths in manifest.json
    'manifest_path_prefix': 'harvard-ftl-shared/PrimarySharedInventoryReport/',
    'private_manifest_path_prefix': 'harvard-ftl-private/PrivateBucketInventory/',
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

### SECURITY

# No need for SECURE_SSL_REDIRECT, because nginx is configured to redirect, and this setting doesn't add any additional
# security since it relies on the same nginx proxy setting X-Forwarded-Proto correctly:
# SECURE_SSL_REDIRECT = True
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# caching
SET_CACHE_CONTROL_HEADER = True

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/%s" % REDIS_DJANGO_CACHE_DB,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}