from .settings_dev import *  # noqa


MAINTAIN_ELASTICSEARCH_INDEX = False  # tests must opt in
ELASTICSEARCH_INDEXES['cases_endpoint'] = 'cases_test'
STORAGES['download_files_storage']['kwargs']['location'] = os.path.join(BASE_DIR, 'test_data/downloads')
SET_CACHE_CONTROL_HEADER = True

# don't waste time on whitenoise for tests
MIDDLEWARE = [i for i in MIDDLEWARE if not i.startswith('whitenoise.')]

SITE_LIMIT_REPORT = True
