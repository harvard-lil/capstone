from .settings_base import *  # noqa

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'k2#@_q=1$(__n7#(zax6#46fu)x=3&^lz&bwb8ol-_097k_rj5'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

MOCK_S3 = True

# don't require celery listener
CELERY_TASK_ALWAYS_EAGER = True
# propagate exceptions
CELERY_TASK_EAGER_PROPAGATES = True



if os.environ.get('DOCKERIZED'):
    DATABASES['default']['PASSWORD'] = 'password'
    DATABASES['default']['HOST'] = 'db'
    DATABASES['capapi']['PASSWORD'] = 'password'
    DATABASES['capapi']['HOST'] = 'db'

    REDIS_HOST = 'redis'

    # this will only be used if CELERY_TASK_ALWAYS_EAGER = False
    CELERY_BROKER_URL = 'redis://redis'
    CELERY_RESULT_BACKEND = 'redis://redis'


# turn sql console logging on by setting DEBUG_SQL = True
DEBUG_SQL = False

if DEBUG_SQL:
    LOGGING['handlers']['sql'] = {
        'level': 'DEBUG',
        'class': 'logging.StreamHandler',
    }
    LOGGING['loggers']['django.db.backends'] = {
        'level': 'DEBUG',
        'handlers': ['sql']
    }

# django-debug-toolbar
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += (
        'debug_toolbar',
    )
    MIDDLEWARE = [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass