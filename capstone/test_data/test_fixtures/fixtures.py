import os
import pytest

from django.conf import settings
from django.test import Client
from django.core.management import call_command
from rest_framework.test import RequestsClient, APIRequestFactory

import fabfile
from capdb.models import VolumeXML, CaseXML, Jurisdiction, Court
import capdb.storages

from . import factories


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
def user():
    return factories.setup_user()

@pytest.fixture
def auth_user():
    return factories.setup_authenticated_user()

@pytest.fixture
def volume_xml():
    return factories.VolumeXMLFactory()

@pytest.fixture
def case():
    return factories.setup_case()

@pytest.fixture
def jurisdiction():
    return factories.setup_jurisdiction()

@pytest.fixture
def court():
    return factories.setup_court()

@pytest.fixture
def reporter():
    return factories.setup_reporter()

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
    # reset caches
    Jurisdiction.reset_cache()
    Court.reset_cache()

    fabfile.ingest_metadata()

@pytest.fixture
def ingest_volumes(ingest_metadata, redis_patch):
    # patch redis client used by ingest_by_manifest
    import scripts.ingest_by_manifest
    scripts.ingest_by_manifest.redis_client, scripts.ingest_by_manifest.r = redis_patch

    # Ingest causes database errors if run in parallel inside test harness.
    # This is probably because database connections have to be closed and reopened by subprocesses, and that triggers
    # a wipe in the test harness.
    scripts.ingest_by_manifest.ASYNC = False

    fabfile.total_sync_with_s3()

@pytest.fixture
def ingest_volume_xml(ingest_volumes):
    return VolumeXML.objects.get(metadata__barcode='32044057892259')

@pytest.fixture
def ingest_case_xml(ingest_volume_xml):
    return ingest_volume_xml.case_xmls.first()

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
