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

    # ours
    'capdb',
    'tracking_tool',
    'capapi',

    # 3rd party
    'storages',  # http://django-storages.readthedocs.io/en/latest/index.html

]

REST_FRAMEWORK = {
    'PAGE_SIZE': 100,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_filters.backends.DjangoFilterBackend',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'capapi.authentication.CAPAPIUserAuthentication',
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

STATIC_URL = '/static/'


# define storages
# each of these can be imported from capdb.storages, e.g. `from capdb.storages import ingest_storage`

STORAGES = {
    'ingest_storage': {
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
    }
}

INVENTORY = {
    # prefix to strip from paths in manifest.json
    'manifest_path_prefix': 'inventory/',
    # prefix to strip from paths in .csv
    'csv_path_prefix': 'from_vendor/',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'api': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/capapi.log',
            'delay': True
        },
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
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
    },
}

### CAP API settings ###

API_CASE_DAILY_ALLOWANCE = 500
API_DOWNLOAD_LIMIT = 100
API_CASE_EXPIRE_HOURS = 24
API_BASE_URL = 'http://localhost:8000'
API_BASE_URL_ROUTE = '/api'
API_VERSION = 'v1'

API_FULL_URL = os.path.join(API_BASE_URL_ROUTE, API_VERSION)
API_CASE_FILE_TYPE = '.xml'

# CAP API EMAIL #
API_ADMIN_EMAIL_ADDRESS = 'main-email-address@example.com'
API_EMAIL_ADDRESS = 'admin-email-address@example.com'

EMAIL_USE_TLS = True
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST_PASSWORD = '123'
EMAIL_HOST_USER = 'user-secret'
EMAIL_HOST_PASSWORD = 'secret-secret'


# redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379