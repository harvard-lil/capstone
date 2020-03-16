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
    'case_image_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'case-images'),
        },
    },
    'transfer_storage': {
        'class': 'CapS3Storage',
        'kwargs': {
            'location': 'to_vendor',
            'bucket_name': 'hlsldigilab-xfer',
        }
    },
    'ngram_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'ngrams'),
        },
    },
    'download_files_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'downloads'),
            'base_url': 'https://case.law/download/',
        }
    },
    'writeable_download_files_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'downloads'),
        }
    }
}

INVENTORY = {
    # prefix to strip from paths in manifest.json
    'manifest_path_prefix': 'harvard-ftl-shared/PrimarySharedInventoryReport/',
    'private_manifest_path_prefix': 'harvard-ftl-private/PrivateBucketInventory/',
}

### API
API_DOCS_CASE_ID = '435800' # Random Illinois case

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

MAILCHIMP = {
    'u': '4290964398813d739f2398db0',
    'id': 'e097736c6f',
    'api_user': '',
    'api_key': ''
}

VALIDATE_EMAIL_SIGNUPS = True

## logging errors via email requires these to be set:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.example.com'
# EMAIL_HOST_USER = 'smtpuser'
# EMAIL_HOST_PASSWORD = 'smtppw'
