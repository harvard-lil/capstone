import os
SECRET_KEY = "secret"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath('capapi/settings.py')))
BASE_URL = 'http://your-url:port'
BASE_API_URL = '/api'
API_VERSION = 'v1'

FULL_API_URL = os.path.join(BASE_API_URL, API_VERSION)
ALLOWED_HOSTS = []
ADMINS = [('Caselaw Access Project', 'info@capapi.org')]
# CAP API specific settings
TOKEN_EXPIRE_HOURS = 24
CASE_DAILY_ALLOWANCE = 500
CASE_EXPIRE_HOURS = 24

AUTH_USER_MODEL = 'capapi.CaseUser'
AUTHENTICATE_FOR_METADATA = False
CASE_FILE_TYPE = '.xml'

CAP_SERVER_TO_CONNECT_TO = '123.45.6.7'
CAP_DATA_DIR_VAR = '$CAP_DATA_DIR'
# TODO: reformat for many states
WHITELISTED_DATA_DIR = '/casemets/illinois'
PRIVATE_KEY_FILENAME = '/path/to/keys'
METADATA_DIR_PATH = '/path/to/dir'
CASE_ZIP_DIR = 'zip_dir'

WHITELISTED_STATES =  ['Illinois']
DOWNLOAD_PAGINATION = 100

APPEND_SLASH = True
EMAIL_USE_TLS = True
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST_PASSWORD = '123'
EMAIL_ADDRESS = 'main-email-address@gmail.com'
ADMIN_EMAIL_ADDRESS = 'admin-email-address@gmail.com'
EMAIL_HOST_USER = 'user-secret'
EMAIL_HOST_PASSWORD = 'secret-secret'

ROOT_URLCONF = 'capapi.urls'

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'capdb',
        'USER': 'capdb',
        'PASSWORD': 'capdb',
        'HOST': '',
        'PORT': '',
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'django_filters',
    'rest_framework',
    'rest_framework.authtoken',
    'pipeline',
    'capapi',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(filename)s %(lineno)d: %(message)s'
        },
    },
    'filters': {
         'require_debug_false': {
             '()': 'django.utils.log.RequireDebugFalse'
         }
     },
    'handlers': {
        'default': {
            'level':'INFO',
            'filters': ['require_debug_false'],
            'class':'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/capdb-api.log',
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True
        },
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.abspath(BASE_DIR + STATIC_URL)

PIPELINE = {
    'CSS_COMPRESSOR':'pipeline.compressors.cssmin.CSSMinCompressor',
    'CSSMIN_BINARY':'cssmin',
    'COMPILERS' : (
        'pipeline.compilers.sass.SASSCompiler',
    ),

    'STYLESHEETS': {
        'base': {
            'source_filenames': (
              'css/raw/_normalize.css',
              'css/raw/_variables.css/raw',
              'css/raw/base.sass',
            ),
            'output_filename': 'css/base.css',
        },
        'docs': {
            'source_filenames': (
              'css/raw/docs.sass',
            ),
            'output_filename': 'css/docs.css',
        },
        'api': {
            'source_filenames': (
              'css/raw/api.sass',
            ),
            'output_filename': 'css/api.css',
        },

    },
}


STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',

)

STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

REST_FRAMEWORK = {
    'PAGE_SIZE' : 100,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': (),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    )
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'capapi', 'templates'), os.path.join(BASE_DIR, 'templates'), ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'capapi.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
