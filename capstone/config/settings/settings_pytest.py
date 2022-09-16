from .settings_dev import *  # noqa

TESTING = True

MAINTAIN_ELASTICSEARCH_INDEX = False  # tests must opt in
ELASTICSEARCH_INDEXES={
    'cases_endpoint': 'cases_test',
    'resolve_endpoint': 'resolve_test',
}
STORAGES['download_files_storage']['kwargs']['location'] = os.path.join(BASE_DIR, 'test_data/downloads')
SET_CACHE_CONTROL_HEADER = True

# don't waste time on whitenoise for tests
MIDDLEWARE = [i for i in MIDDLEWARE if not i.startswith('whitenoise.')]

SITE_LIMIT_REPORT = True

# use a fast password hash by default for speed
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
] + PASSWORD_HASHERS

# avoid test errors when running tests locally, since pytest-django sets DEBUG=False and staticfiles/ doesn't exist
STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

# https://github.com/pytest-dev/pytest-django/blob/fba51531f067a985ec6b6be4aec9a2ed5766d69c/pytest_django/live_server_helper.py#L35
INSTALLED_APPS.remove('django.contrib.staticfiles')
