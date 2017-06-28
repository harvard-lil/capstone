# copied to settings.py by .travis.yml:

from .settings_dev import *

# disable ssl to avoid postgres connection error for pytest
DATABASES['default'].setdefault('OPTIONS', {})
DATABASES['default']['OPTIONS']['sslmode'] = 'disable'
