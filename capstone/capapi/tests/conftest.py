import pytest
from django.core.management import call_command


@pytest.fixture
def load_parsed_metadata():
    print("loading parsed metadata")
    call_command('loaddata', 'test_data/parsed_metadata.json')


@pytest.fixture
def load_user_data():
    print("loading user metadata")
    call_command('loaddata', 'test_data/user_data.json')
