import pytest
from django.core.management import call_command

import fabfile
from capdb.models import VolumeXML


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
def ingest_volumes(ingest_metadata):
    fabfile.total_sync_with_s3()

@pytest.fixture
def volume_xml(ingest_volumes):
    return VolumeXML.objects.get(barcode='32044057892259')

@pytest.fixture
def case_xml(volume_xml):
    return volume_xml.case_xmls.first()