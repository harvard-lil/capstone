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
# if running in Docker -- this will only be used if CELERY_TASK_ALWAYS_EAGER = False
CELERY_BROKER_URL = 'amqp://admin:mypass@rabbit'
CELERY_RESULT_BACKEND = 'rpc://'