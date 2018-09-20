# copied to settings.py by .travis.yml:

from .settings_dev import *

# disable ssl to avoid postgres connection error for pytest
DATABASES['default'].setdefault('OPTIONS', {})
DATABASES['default']['OPTIONS']['sslmode'] = 'disable'

DEBUG = False
ALLOWED_HOSTS = ['*']

# Use production django-pipeline storage. This works because Travis runs collectstatic.
STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
