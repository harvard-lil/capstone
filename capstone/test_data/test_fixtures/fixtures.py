from collections import defaultdict
from urllib.parse import urlparse
from time import time

import mock
import pytest
from django.contrib import auth
from django.contrib.auth.models import Group
from django.core.signals import request_started, request_finished
from django.core.cache import cache as django_cache
from django.core.management import call_command
from django.db import connections
import django.apps
from django.utils.functional import SimpleLazyObject
from moto import mock_s3
from rest_framework.test import APIRequestFactory, APIClient
from elasticsearch_dsl import Index as es_index
from capapi.documents import CaseDocument

# Before importing any of our code, mock capdb.storages redis clients.
# Do this here so anything that gets imported later will get the mocked versions.
import capdb.storages


def raise_not_implemented(): raise NotImplementedError("Cannot access redis client outside of test")


capdb.storages.redis_client = SimpleLazyObject(raise_not_implemented)
capdb.storages.redis_ingest_client = SimpleLazyObject(raise_not_implemented)

# our packages
import fabfile
from .factories import *


### Database setup ###

# This is run once at database setup and data loaded here is available to all tests
# See http://pytest-django.readthedocs.io/en/latest/database.html#populate-the-database-with-initial-test-data
# Note that the documentation is currently misleading in that this function cannot create data (that seems to
# deleted with each test), but can set up things like functions and triggers.
@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker, redis_proc):
    from django.test import TransactionTestCase, TestCase
    # This is a hack around pytest not playing nice with multiple databases
    # Without these flags set, we don't get any non-default database cleanup
    # in between tests
    # https://github.com/pytest-dev/pytest-django/issues/76
    TransactionTestCase.multi_db = True
    TestCase.multi_db = True

    with django_db_blocker.unblock():
        # set up postgres functions and triggers
        fabfile.update_postgres_env()


@pytest.fixture(autouse=True)
def clear_caches(request):
    """ Clear any caches that might affect later tests. """

    # patch redis clients to point to test-specific redis mock
    import pytest_redis.factories
    capdb.storages.redis_client._wrapped = SimpleLazyObject(
        lambda: pytest_redis.factories.redisdb('redis_proc', db=settings.REDIS_DEFAULT_DB)(request))
    capdb.storages.redis_ingest_client._wrapped = SimpleLazyObject(
        lambda: pytest_redis.factories.redisdb('redis_proc', db=settings.REDIS_INGEST_DB)(request))

    try:
        yield
    finally:
        # clear django cache
        django_cache.clear()

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
    from django.test.utils import CaptureQueriesContext

    @contextmanager
    def _assert_num_queries(db='capdb', **expected_counts):
        conn = connections[db]
        with CaptureQueriesContext(conn) as context:
            yield
            query_counts = defaultdict(int)
            for q in context.captured_queries:
                query_type = q['sql'].split(" ", 1)[0].lower()
                if query_type not in ('savepoint', 'release', 'set', 'show'):
                    query_counts[query_type] += 1
            if expected_counts != query_counts:
                msg = "Unexpected queries: expected %s, got %s" % (expected_counts, dict(query_counts))
                if pytestconfig.getoption('verbose') > 0:
                    msg += '\n\nQueries:\n========\n\n'
                    for q in context.captured_queries:
                        if q['userland_stack_frame']:
                            msg += "%s:%s:\n%s\n" % (
                                q['userland_stack_frame'].filename,
                                q['userland_stack_frame'].lineno,
                                q['userland_stack_frame'].code_context[0].rstrip())
                        else:
                            msg += "Not via userland:\n"
                        short_sql = re.sub(r'\'.*?\'', "'<str>'", q['sql'], flags=re.DOTALL)
                        msg += "%s\n\n" % short_sql
                else:
                    msg += " (add -v option to show queries)"
                pytest.fail(msg)

    return _assert_num_queries


@pytest.fixture
def benchmark_requests():
    """
        Context manager to get a report of the time taken to process each request inside the block.
        This is better than measuring the time directly because it doesn't include time used by the test client.
        Example:

            @pytest.mark.django_db
            def test_profile_cases(client, benchmark_requests):
                url = api_reverse('casemetadata-list')
                with benchmark_requests() as times:
                    for i in range(50):
                        client.get(url)
                print("Average: %s" % (sum(times)/len(times)))
                print("Min: %s" % min(times))
    """

    @contextmanager
    def do_benchmark():
        start_times = []
        times = []

        def handle_started(*args, **kwargs):
            start_times.append(time())

        def handle_finished(*args, **kwargs):
            times.append(time() - start_times[-1])

        request_started.connect(handle_started)
        request_finished.connect(handle_finished)
        try:
            yield times
        finally:
            request_started.disconnect(handle_started)
            request_finished.disconnect(handle_finished)

    return do_benchmark


### file contents ###

@pytest.fixture
def unaltered_alto_xml():
    """ XML from an alto file we haven't modified at all. """
    with open(os.path.join(settings.BASE_DIR, 'test_data/unaltered_32044057891608_redacted_ALTO_00009_1.xml'),
              'rb') as in_file:
        return in_file.read()


@pytest.fixture
def s3_storage():
    with mock_s3():
        yield capdb.storages.CapS3Storage(
            auto_create_bucket=True,
            bucket_name='bucket',
            location='subdir',
        )


@pytest.fixture
def file_storage(tmpdir):
    return capdb.storages.CapFileStorage(location=str(tmpdir))


@pytest.fixture
def mock_ngram_storage(tmpdir):
    with mock.patch('capdb.storages.ngram_kv_store._wrapped', SimpleLazyObject(lambda: capdb.storages.NgramRocksDB(path=str(tmpdir)))), \
            mock.patch('capdb.storages.ngram_kv_store_ro._wrapped', SimpleLazyObject(lambda: capdb.storages.NgramRocksDB(path=str(tmpdir), read_only=True))):
        yield None


@pytest.fixture
def ngrammed_cases(mock_ngram_storage, three_cases, jurisdiction):
    import scripts.ngrams

    # set up two jurisdictions
    jur0 = jurisdiction
    jur0.slug = 'jur0'
    jur0.save()
    jur1 = three_cases[0].jurisdiction
    jur1.slug = 'jur1'
    jur1.save()

    # set up three cases across two jurisdictions, all in same year
    case_settings = [
        (jur0, '"One? two three." Four!', 2000),
        (jur1, "One 'two three' don't.", 2000),
        (jur1, "(Two, three, don't, don't)", 2000),
    ]
    for case, (jur, text, year) in zip(three_cases, case_settings):
        case.jurisdiction = jur
        case.jurisdiction_slug = jur.slug  # something about the test env is stopping the trigger from setting this
        case.decision_date = case.decision_date.replace(year=year)
        case.save()
        CaseBodyCache(metadata=case, text=text).save()

    # run ngram code
    scripts.ngrams.ngram_jurisdictions()
    scripts.ngrams.ngram_kv_store_ro.open()  # re-open so we can see the new values

    return three_cases
        
### Django json fixtures ###

@pytest.fixture
def load_tracking_tool_database():
    call_command('loaddata', 'test_data/tracking_tool.json', database='tracking_tool')


### Factory fixtures ###
@pytest.fixture
def case(case_xml):
    return case_xml.metadata


@pytest.fixture
def case_metadata():
    """
        This should be provided by @register on CaseFactory, but for some reason that version currently fails to
        pass itself to the RelatedFactory attributes, and thus throws an IntegrityError.
    """
    return CaseFactory()


@pytest.fixture
def three_cases():
    return [CaseXMLFactory().metadata for _ in range(3)]


@pytest.fixture
def auth_user(token):
    token.user.email_verified = True
    token.user.save()
    return token.user


class CapClient(APIClient):
    def generic(self, method, path, *args, **kwargs):
        # make test client use domain portion of path to set HTTP_HOST, so subdomain routing works
        parsed = urlparse(str(path))
        if parsed.netloc:
            kwargs.setdefault('HTTP_HOST', parsed.netloc)
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def client():
    return CapClient()


@pytest.fixture
def auth_client(auth_user):
    """ Return client authenticated as auth_user, via Django session. """
    client = CapClient()
    client.force_login(user=auth_user)
    # make user available to tests
    client.auth_user = auth_user
    return client


@pytest.fixture
def token_auth_client(auth_user):
    """ Return client authenticated as auth_user, via token. """
    client = CapClient()
    client.credentials(HTTP_AUTHORIZATION='Token ' + auth_user.get_api_key())
    # make user available to tests
    client.auth_user = auth_user
    return client


@pytest.fixture
def unlimited_auth_client(auth_client):
    user = auth_client.auth_user
    user.unlimited_access = True
    user.unlimited_access_until = timezone.now() + timedelta(days=1)
    user.save()
    return auth_client


@pytest.fixture
def contract_approver_auth_client():
    client = CapClient()
    user = CapUserFactory(email_verified=True)
    client.force_login(user)
    client.auth_user = user
    user.groups.add(Group.objects.get_or_create(name='contract_approvers')[0])
    return client


@pytest.fixture
def api_request_factory():
    return APIRequestFactory()


@pytest.fixture()
def admin_user(db, django_user_model, django_username_field):
    # Overwrite of pytest's Django admin_user fixture because
    # we're using email as username_field
    UserModel = django_user_model
    username_field = django_username_field

    try:
        user = UserModel._default_manager.get(**{username_field: 'admin@example.com'})
    except UserModel.DoesNotExist:
        extra_fields = {}
        user = UserModel._default_manager.create_superuser(
            'test_admin_user@example.com', 'password', **extra_fields)
    return user


@pytest.fixture()
def staff_user(cap_user):
    cap_user.is_staff = True
    cap_user.save()
    return cap_user


@pytest.fixture
def anonymous_user(client):
    user = auth.get_user(client)
    return user


@pytest.fixture()
def anonymous_client(client, anonymous_user):
    client.user = anonymous_user
    return client


@pytest.fixture()
def admin_client(db, admin_user):
    # Overwrite of pytest's Django admin_client
    from django.test.client import Client

    client = Client()
    client.login(email=admin_user.email, password='password')
    return client


@pytest.fixture()
def private_case_export():
    return CaseExportFactory.create(public=False)


### DATA INGEST FIXTURES ###

@pytest.fixture
def ingest_metadata(load_tracking_tool_database):
    fabfile.ingest_metadata()


@pytest.fixture
def ingest_volumes(ingest_metadata):
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
    return [{"caseid": "32044057892259_0001", "id": "b15-13", "barcode": "32044057892259",
             "content": "Appeal from the Circuit Court of Woodford County; the lion. T. M. Shaw, Judge, presiding."},
            {"caseid": "32044057891608_0001", "id": "b17-14", "barcode": "32044057891608",
             "content": "* Justice Browne having decided this cause in the court below, gave no opinion."}]


@pytest.fixture
def invalid_mass_casebody_tag_rename():
    return [{"caseid": "32044057892259_0001", "id": "b15-13", "barcode": "32044057892259",
             "content": "Appeal from the Circuit Court of Woodford County; the lion. T. M. Shaw, Judge, presiding."},
            {"caseid": "32044057891608_0001", "id": "b17-14", "barcode": "32044057891608",
             "content": "* Justice Browne having decided this cause in the court below, gave no opinion."},
            {"caseid": "32044061407086_0001", "id": "b178-7", "barcode": "32044061407086",
             "content": "Before ALDRICH, Chief Judge, Mc­ENTEE and COFFIN, Circuit Judges."}]


@pytest.fixture
def inline_image_src():
    return """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 """

@pytest.fixture()
def ingest_elasticsearch(load_tracking_tool_database):
    call_command('loaddata', 'test_data/jurisdiction.json', database='capdb')
    call_command('loaddata', 'test_data/reporter.json', database='capdb')
    call_command('loaddata', 'test_data/court.json', database='capdb')
    call_command('loaddata', 'test_data/volume_metadata.json', database='capdb')
    call_command('loaddata', 'test_data/case_metadata.json', database='capdb')
    call_command('loaddata', 'test_data/body_cache.json', database='capdb')
    call_command('loaddata', 'test_data/citation.json', database='capdb')
    fabfile.rebuild_search_index(force=True)

    # Make sure these cases are accessible
    while es_index("cases_test").stats()['_all']['total']['docs']['count'] < 3:
        continue

    yield
    call_command('search_index', '--delete', '-f')


@pytest.fixture
def taylor_v_sprinkle(ingest_elasticsearch):
    return {
        "id": 312,
        "case_id": "32044057891608_0001",
        "frontend_url": "/ill/1/17/",
        "first_page": "17",
        "last_page": "18",
        "publication_status": "published",
        "jurisdiction": 29,
        "judges": [],
        "parties": [
            "Jonathan Taylor, Appellant, v. Michael Sprinkle, Appellee."
        ],
        "opinions": [
            {
                "author": None,
                "type": "majority"
            }
        ],
        "attorneys": [],
        "docket_number": "",
        "docket_numbers": [],
        "decision_date": "1819-12-01",
        "decision_date_original": "1819-12",
        "argument_date_original": None,
        "court": 3,
        "district_name": None,
        "district_abbreviation": None,
        "name": "Jonathan Taylor, Appellant, v. Michael Sprinkle, Appellee",
        "name_abbreviation": "Taylor v. Sprinkle",
        "volume": "32044057891608",
        "reporter": 1058,
        "date_added": "2019-10-01T17:03:17.852Z",
        "duplicative": False,
        "duplicate": False,
        "duplicate_of": None,
        "withdrawn": False,
        "replaced_by": None,
        "no_index": False,
        "no_index_notes": None,
        "in_scope": True,
        "initial_metadata_synced": True,
        "jurisdiction_name": "Ill.",
        "jurisdiction_name_long": "Illinois",
        "jurisdiction_slug": "ill",
        "jurisdiction_whitelisted": True,
        "court_name": "Illinois Supreme Court",
        "court_name_abbreviation": "Ill.",
        "court_slug": "ill",
        "sys_period": "{\"bounds\": \"[)\", \"lower\": \"2019-10-01T17:54:28.706957+00:00\", \"upper\": null}"
    }



@pytest.fixture
def home_insurance_co_of_new_york_v_kirk(ingest_elasticsearch):
    return {
        "id": 311,
        "case_id": "32044057892259_0001",
        "frontend_url": "/ill-app/23/19/",
        "first_page": "19",
        "last_page": "24",
        "publication_status": "published",
        "jurisdiction": 29,
        "judges": [],
        "parties": [
            "The Home Insurance Company of New York v. John Kirk, for use of William Kirk."
        ],
        "opinions": [
            {
                "author": "Lacey, J.",
                "type": "majority"
            }
        ],
        "attorneys": [
            "Mr. Walter Bennett, for appellant.",
            "Messrs. J. A. Biely and Barnes & Barnes, for appellee."
        ],
        "docket_number": "",
        "docket_numbers": [],
        "decision_date": "1887-05-27",
        "decision_date_original": "1887-05-27",
        "argument_date_original": None,
        "court": 2,
        "district_name": None,
        "district_abbreviation": None,
        "name": "The Home Insurance Company of New York v. John Kirk, for use of William Kirk",
        "name_abbreviation": "Home Insurance Co. of New York v. Kirk",
        "volume": "32044057892259",
        "reporter": 315,
        "date_added": "2019-10-01T17:03:16.973Z",
        "duplicative": False,
        "duplicate": False,
        "duplicate_of": None,
        "withdrawn": False,
        "replaced_by": None,
        "no_index": False,
        "no_index_notes": None,
        "in_scope": True,
        "initial_metadata_synced": True,
        "jurisdiction_name": "Ill.",
        "jurisdiction_name_long": "Illinois",
        "jurisdiction_slug": "ill",
        "jurisdiction_whitelisted": True,
        "court_name": "Illinois Appellate Court",
        "court_name_abbreviation": "Ill. App. Ct.",
        "court_slug": "ill-app-ct",
        "sys_period": "{\"bounds\": \"[)\", \"lower\": \"2019-10-01T17:54:28.706957+00:00\", \"upper\": null}"
    }



@pytest.fixture
def in_re_the_marriage_of_lyle(ingest_elasticsearch):
    return {
        "id": 309,
        "case_id": "WnApp_199_0036",
        "frontend_url": "/wash-app/199/629/",
        "first_page": "629",
        "last_page": "634",
        "publication_status": "published",
        "jurisdiction": 38,
        "judges": [
            "Fearing, C.J., and Korsmo, J., concur."
        ],
        "parties": [
            "In the Matter of the Marriage of Christy Lyle, Respondent, and Keith Lyle, Appellant."
        ],
        "opinions": [
            {
                "author": "Pennell, J.",
                "type": "majority"
            }
        ],
        "attorneys": [
            "Matthew J. Dudley, for appellant.",
            "Camerina I. Brokaw-Zorrozua (of Maxey Law Office PS), for respondent."
        ],
        "docket_number": "No. 33971-8-III",
        "docket_numbers": [
            "No. 33971-8-III"
        ],
        "decision_date": "2017-07-11",
        "decision_date_original": "2017-07-11",
        "argument_date_original": None,
        "court": 1,
        "district_name": None,
        "district_abbreviation": None,
        "name": "In the Matter of the Marriage of Christy Lyle, Respondent, and Keith Lyle, Appellant",
        "name_abbreviation": "In re the Marriage of Lyle",
        "volume": "WnApp_199",
        "reporter": 477,
        "date_added": "2019-10-01T17:03:15.620Z",
        "duplicative": False,
        "duplicate": False,
        "duplicate_of": None,
        "withdrawn": False,
        "replaced_by": None,
        "no_index": False,
        "no_index_notes": None,
        "in_scope": True,
        "initial_metadata_synced": True,
        "jurisdiction_name": "Wash.",
        "jurisdiction_name_long": "Washington",
        "jurisdiction_slug": "wash",
        "jurisdiction_whitelisted": False,
        "court_name": "Washington Court of Appeals",
        "court_name_abbreviation": "Wash. Ct. App.",
        "court_slug": "wash-ct-app",
        "sys_period": "{\"bounds\": \"[)\", \"lower\": \"2019-10-01T17:54:28.706957+00:00\", \"upper\": null}"
    }

@pytest.fixture
def es_non_whitelisted_case(in_re_the_marriage_of_lyle):
    return in_re_the_marriage_of_lyle

@pytest.fixture
def es_whitelisted_case(home_insurance_co_of_new_york_v_kirk):
    return home_insurance_co_of_new_york_v_kirk

@pytest.fixture
def es_three_cases(in_re_the_marriage_of_lyle, home_insurance_co_of_new_york_v_kirk, taylor_v_sprinkle):
    return [in_re_the_marriage_of_lyle, home_insurance_co_of_new_york_v_kirk, taylor_v_sprinkle]


@pytest.fixture
def es_duplicative_case(ingest_elasticsearch):
    return {
        "id": "310",
        "case_id": "32044061407086_0001",
        "frontend_url": "/nw2d/60/1/",
        "first_page": "1",
        "last_page": "4",
        "publication_status": None,
        "jurisdiction": None,
        "judges": None,
        "parties": None,
        "opinions": None,
        "attorneys": None,
        "docket_number": "",
        "docket_numbers": None,
        "decision_date": None,
        "decision_date_original": "",
        "argument_date_original": None,
        "court": None,
        "district_name": None,
        "district_abbreviation": None,
        "name": "",
        "name_abbreviation": "",
        "volume": "32044061407086",
        "reporter": 892,
        "date_added": "2019-10-01T17:03:16.271Z",
        "duplicative": True,
        "duplicate": False,
        "duplicate_of": None,
        "withdrawn": False,
        "replaced_by": None,
        "no_index": False,
        "no_index_notes": None,
        "in_scope": False,
        "initial_metadata_synced": False,
        "jurisdiction_name": None,
        "jurisdiction_name_long": None,
        "jurisdiction_slug": None,
        "jurisdiction_whitelisted": None,
        "court_name": None,
        "court_name_abbreviation": None,
        "court_slug": None,
        "sys_period": "{\"bounds\": \"[)\", \"lower\": \"2019-10-01T17:54:28.706957+00:00\", \"upper\": null}"
    }

@pytest.fixture
def case_document(es_whitelisted_case):
    return CaseDocument.get(id=es_whitelisted_case['id'])

@pytest.fixture
def duplicative_case_document(es_duplicative_case):
    return CaseDocument.get(id=es_duplicative_case['id'])

@pytest.fixture
def three_case_documents(es_three_cases):
    return [CaseDocument.get(id=case['id']) for case in es_three_cases]


