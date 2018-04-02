from collections import defaultdict
from contextlib import contextmanager

import pytest

from django.test import Client
from django.core.management import call_command
import django.apps
from rest_framework.test import RequestsClient, APIRequestFactory

import fabfile
import capdb.storages

from .factories import *

### Database setup ###

# This is run once at database setup and data loaded here is available to all tests
# See http://pytest-django.readthedocs.io/en/latest/database.html#populate-the-database-with-initial-test-data
# Note that the documentation is currently misleading in that this function cannot create data (that seems to
# deleted with each test), but can set up things like functions and triggers.
@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker, redis_proc):
    with django_db_blocker.unblock():

        # set up postgres functions and triggers
        fabfile.update_postgres_env()

@pytest.fixture(autouse=True)
def clear_caches():
    """ Clear any caches that might affect later tests. """
    try:
        yield
    finally:
        # call reset_cache for all models that have it:
        for model in django.apps.apps.get_models():
            if hasattr(model, 'reset_cache'):
                model.reset_cache()

@pytest.fixture(scope='function')
def django_assert_num_queries(pytestconfig):
    """
        via https://github.com/pytest-dev/pytest-django/pull/387
        modified to specify individual query types

        Provide a context manager to assert which queries will be run by a block of code. Example:

            def test_foo(django_assert_num_queries):
                with django_assert_num_queries(select=1, update=2):
                    # run one select and two updates

        This tests only the default database.

        Suggestions for adding this to existing tests: start by running with counts empty:

            with django_assert_num_queries():

        Run the test as:

            pytest -k test_foo -v

        Ensure that the queries run are as expected, then insert the correct counts based on the error message.
    """
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    @contextmanager
    def _assert_num_queries(**expected_counts):
        with CaptureQueriesContext(connection) as context:
            yield
            query_counts = defaultdict(int)
            for q in context.captured_queries:
                query_type = q['sql'].split(" ",1)[0].lower()
                if query_type not in ('savepoint', 'release'):
                    query_counts[query_type] += 1
            if expected_counts != query_counts:
                msg = "Unexpected queries: expected %s, got %s" % (expected_counts, dict(query_counts))
                if pytestconfig.getoption('verbose') > 0:
                    sqls = (q['sql'] for q in context.captured_queries)
                    msg += '\n\nQueries:\n========\n\n%s' % '\n\n'.join(sqls)
                else:
                    msg += " (add -v option to show queries)"
                pytest.fail(msg)

    return _assert_num_queries


### file contents ###

@pytest.fixture
def unaltered_alto_xml():
    """ XML from an alto file we haven't modified at all. """
    with open(os.path.join(settings.BASE_DIR, 'test_data/unaltered_32044057891608_redacted_ALTO_00009_1.xml'), 'rb') as in_file:
        return in_file.read()


### Django json fixtures ###

@pytest.fixture
def load_user_data():
    call_command('loaddata', 'test_data/user_data.json')

@pytest.fixture
def load_tracking_tool_database():
    call_command('loaddata', 'test_data/tracking_tool.json', database='tracking_tool')


### Factory fixtures ###
@pytest.fixture
def case(case_xml):
    return case_xml.metadata

@pytest.fixture
def three_cases():
    return [CaseXMLFactory().metadata for _ in range(3)]

@pytest.fixture
def auth_user(api_token):
    user = APIUserFactory()
    token = APITokenFactory(user=user)
    return user

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def auth_client():
    return RequestsClient()

@pytest.fixture
def api_url():
    return "http://testserver" + settings.API_FULL_URL + "/"

@pytest.fixture
def api_request_factory():
    return APIRequestFactory()


### REDIS ###

@pytest.fixture
def redis_patch(request):
    import pytest_redis.factories

    capdb.storages.redis_client = pytest_redis.factories.redisdb('redis_proc', db=settings.REDIS_DEFAULT_DB)(request)
    capdb.storages.redis_ingest_client = pytest_redis.factories.redisdb('redis_proc', db=settings.REDIS_INGEST_DB)(request)
    return capdb.storages.redis_client, capdb.storages.redis_ingest_client


### DATA INGEST FIXTURES ###

@pytest.fixture
def ingest_metadata(load_tracking_tool_database):
    fabfile.ingest_metadata()

@pytest.fixture
def ingest_volumes(ingest_metadata, redis_patch):
    # patch redis client used by ingest_by_manifest
    import scripts.ingest_by_manifest
    scripts.ingest_by_manifest.redis_client, scripts.ingest_by_manifest.r = redis_patch

    fabfile.total_sync_with_s3()

@pytest.fixture
def ingest_volume_xml(ingest_volumes):
    return VolumeXML.objects.get(metadata__barcode='32044057892259')

@pytest.fixture
def ingest_case_xml(ingest_volume_xml):
    return CaseXML.objects.get(metadata__case_id='32044057892259_0001')

@pytest.fixture
def ingest_duplicative_case_xml(ingest_volumes):
    return CaseXML.objects.get(metadata__case_id='32044061407086_0001')

@pytest.fixture
def valid_mass_casebody_tag_rename():
    return [{"caseid":"32044057892259_0001","id":"b15-13","barcode":"32044057892259","content":"Appeal from the Circuit Court of Woodford County; the lion. T. M. Shaw, Judge, presiding."},
            {"caseid":"32044057891608_0001","id":"b17-14","barcode":"32044057891608","content":"* Justice Browne having decided this cause in the court below, gave no opinion."}]

@pytest.fixture
def invalid_mass_casebody_tag_rename():
    return [{"caseid":"32044057892259_0001","id":"b15-13","barcode":"32044057892259","content":"Appeal from the Circuit Court of Woodford County; the lion. T. M. Shaw, Judge, presiding."},
            {"caseid":"32044057891608_0001","id":"b17-14","barcode":"32044057891608","content":"* Justice Browne having decided this cause in the court below, gave no opinion."},
            {"caseid":"32044061407086_0001","id":"b178-7","barcode":"32044061407086","content":"Before ALDRICH, Chief Judge, Mc­ENTEE and COFFIN, Circuit Judges."}]
