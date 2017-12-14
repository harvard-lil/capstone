import pytest

from django.conf import settings
from django.test import Client
from django.core.management import call_command
from rest_framework.test import RequestsClient, APIRequestFactory

import fabfile
from capdb.models import VolumeXML, CaseXML, Jurisdiction, Court
import capdb.storages

from . import factories


### Django json fixtures ###

@pytest.fixture
def load_parsed_metadata():
    call_command('loaddata', 'test_data/parsed_metadata.json')


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
def redis_patch(redisdb):
    capdb.storages.redis_client = redisdb
    return capdb.storages.redis_client


### DATA INGEST FIXTURES ###

@pytest.fixture
def ingest_metadata(load_tracking_tool_database):
    fabfile.ingest_metadata()

@pytest.fixture
def ingest_volumes(ingest_metadata, redis_patch):
    # patch redis client used by ingest_by_manifest
    import scripts.ingest_by_manifest
    scripts.ingest_by_manifest.r = redis_patch

    # Ingest causes database errors if run in parallel inside test harness.
    # This is probably because database connections have to be closed and reopened by subprocesses, and that triggers
    # a wipe in the test harness.
    scripts.ingest_by_manifest.ASYNC = False

    # reset caches
    Jurisdiction.reset_cache()
    Court.reset_cache()

    fabfile.total_sync_with_s3()

@pytest.fixture
def volume_xml(ingest_volumes):
    return VolumeXML.objects.get(metadata__barcode='32044057892259')

@pytest.fixture
def case_xml(volume_xml):
    return volume_xml.case_xmls.first()

@pytest.fixture
def duplicative_case_xml(ingest_volumes):
    return CaseXML.objects.get(metadata__case_id='32044061407086_0001')