import pytest
from django.core.management import call_command


@pytest.fixture
def load_parsed_metadata():
    call_command('loaddata', 'test_data/parsed_metadata.json')

