import os
from settings_deployments.settings_common import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = 'http://localhost:8000'
DEBUG = True
SECRET_KEY = 'secret'

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cap',
        'USER': 'cap',
        'PASSWORD': 'cap',
        'HOST': '',
        'PORT': '',
    }
}


# Static files (CSS, JavaScript, Images)
# https://docs].djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '../static/'
STATIC_ROOT = os.path.join(BASE_DIR, STATIC_URL)

STATICFILES_FINDERS = (
    'compressor.finders.CompressorFinder',
)

APPEND_SLASH=True

COMPRESS_PRECOMPILERS = (
    ('text/x-scss', 'django_libsass.SassCompiler'),
)
COMPRESS_ENABLED = True
