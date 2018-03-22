import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ALLOWED_HOSTS = []

ADMINS = [('Caselaw Access Project', 'info@capapi.org')]


# Application definition

INSTALLED_APPS = [
    # built in
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_filters',
    'django_extensions',
    'rest_framework',
    'rest_framework.authtoken',
    'pipeline',

    # ours
    'capdb',
    'tracking_tool',
    'capapi',

    # 3rd party
    'storages',  # http://django-storages.readthedocs.io/en/latest/index.html
    'simple_history',   # model versioning
]

REST_FRAMEWORK = {
    'PAGE_SIZE': 100,
    'DEFAULT_PAGINATION_CLASS': 'capapi.pagination.CountlessPagination',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_filters.backends.DjangoFilterBackend',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'capapi.authentication.CAPAPIUserAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'capapi.permissions.IsSafeMethodsUser',
    ),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'capdb.middleware.login_required_middleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'capapi', 'templates')], # required by DRF for some reason
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

USE_TEST_TRACKING_TOOL_DB = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'capstone',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    },
    'capapi': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'capapi',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    },
    'tracking_tool': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'test_data/tracking_tool.sqlite'),
    }
}

# make sure tracking_tool app uses tracking_tool DB:
DATABASE_ROUTERS = [
    'capapi.routers.CAPAPIRouter',
    'tracking_tool.routers.TrackingToolDatabaseRouter',
]

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'pipeline.finders.PipelineFinder',
)

PIPELINE = {
    'ENABLED': True,
    'COMPILERS': ('pipeline.compilers.sass.SASSCompiler',),
    'STYLESHEETS': {
        'base': {
            'source_filenames': (
                'css/_normalize.css',
                'css/scss/base.scss',
            ),
            'output_filename': 'css/base.css',
        },
        'docs': {
            'source_filenames': (
                'css/scss/docs.scss',
            ),
            'output_filename': 'css/docs.css',
        }
    },
}

# define storages
# each of these can be imported from capdb.storages, e.g. `from capdb.storages import ingest_storage`

STORAGES = {
    'ingest_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'test_data/from_vendor'),
        },
    },
    'private_ingest_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'test_data/from_vendor'),
        },
    },
    'inventory_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'test_data/inventory'),
        },
    },
    'private_inventory_storage': {
        'class': 'CapFileStorage',
        'kwargs': {
            'location': os.path.join(BASE_DIR, 'test_data/inventory'),
        },
    },
}

INVENTORY = {
    # prefix to strip from paths in manifest.json
    'manifest_path_prefix': 'inventory/',
    'private_manifest_path_prefix': 'inventory/',
}

### CELERY ###
CELERY_BROKER_URL = 'redis://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_BACKEND = 'redis://'
CELERY_TASK_SERIALIZER = 'json'


### CAP API settings ###

API_CASE_DAILY_ALLOWANCE = 500
API_DOWNLOAD_LIMIT = 100
API_CASE_EXPIRE_HOURS = 24
API_BASE_URL = 'http://localhost:8000'
API_BASE_URL_ROUTE = '/api'
API_VERSION = 'v1'
API_DOCS_CASE_ID = 2

API_FULL_URL = os.path.join(API_BASE_URL_ROUTE, API_VERSION)
API_CASE_FILE_TYPE = '.xml'

# CAP API EMAIL #
API_ADMIN_EMAIL_ADDRESS = 'main-email-address@example.com'
API_EMAIL_ADDRESS = 'admin-email-address@example.com'

EMAIL_USE_TLS = True
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST_USER = 'user-secret'
EMAIL_HOST_PASSWORD = 'secret-secret'


# redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
# redis by default has 16 databases, numbered 0-15:
REDIS_DEFAULT_DB = 0
REDIS_INGEST_DB = 1     # database for temporary data created during the S3 ingest process


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'api': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/capapi.log',
            'delay': True
        },

        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'capapi': {
            'handlers': ['api'],
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        # silence boto3 info logging -- see https://github.com/boto/boto3/issues/521
        'boto3': {
            'level': 'WARNING',
        },
        'botocore': {
            'level': 'WARNING',
        },
        'nose': {
            'level': 'WARNING',
        },
        's3transfer': {
            'level': 'WARNING',
        },

    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s module=%(module)s, '
            'process_id=%(process)d, %(message)s'
        }
    },
}


# if celery is launched with --autoscale=1000, celery will autoscale to 1000 but limited by system resources:
CELERY_WORKER_AUTOSCALER = 'celery_resource_autoscaler:ResourceAutoscaler'
CELERY_RESOURCE_LIMITS = [
    {
        'class': 'celery_resource_autoscaler:MemoryLimit',
        'kwargs': {'max_memory': 0.8},
    },
    {
        'class': 'celery_resource_autoscaler:CPULimit',
        'kwargs': {'max_load': 0.8},
    },
]

# security
SECURE_CONTENT_TYPE_NOSNIFF = True

SILENCED_SYSTEM_CHECKS = [
    "models.E004"   # For our history tables, the "id" field should not be a primary key. This disables the Django system
                    # check that required "id" fields to be primary keys.
]

