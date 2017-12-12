import pytest
from django.core.management import call_command

import fabfile
from capdb.models import VolumeXML, CaseXML
import capdb.storages


### REDIS ###

@pytest.fixture
def redis_patch(redisdb):
    capdb.storages.redis_client = redisdb
    return capdb.storages.redis_client


### DATA INGEST FIXTURES ###

# This stack of fixtures loads the tracking tool db, volume metadata, volume data, and a sample volume.
# Each fixture calls the one above it.

@pytest.fixture
def load_tracking_tool_database():
    call_command('loaddata', 'test_data/tracking_tool.json', database='tracking_tool')

@pytest.fixture
def load_parsed_metadata():
    call_command('loaddata', 'test_data/parsed_metadata.json')

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