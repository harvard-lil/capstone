import pytest
from django.test import Client
from django.conf import settings
from django.core.management import call_command
from rest_framework.test import RequestsClient, APIRequestFactory

from test_data import factories

@pytest.fixture
def load_parsed_metadata():
    call_command('loaddata', 'test_data/parsed_metadata.json')


@pytest.fixture
def load_user_data():
    call_command('loaddata', 'test_data/user_data.json')


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

