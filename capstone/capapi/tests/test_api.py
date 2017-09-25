import json
import pytest

from django.test import Client
from django.conf import settings

from capdb.models import CaseMetadata


@pytest.mark.django_db
def test_api_urls(load_parsed_metadata):
    c = Client()
    response = c.get('%s/cases/' % settings.API_FULL_URL)
    assert response.status_code == 200
    assert response.accepted_renderer.format != 'json'
    response = c.get('%s/cases/?format=json' % settings.API_FULL_URL)
    assert response.status_code == 200
    assert response.accepted_renderer.format == 'json'
    response = c.get('%s/jurisdictions/' % settings.API_FULL_URL)
    assert response.accepted_renderer.format != 'json'
    assert response.status_code == 200
    response = c.get('%s/jurisdictions/?format=json' % settings.API_FULL_URL)
    assert response.status_code == 200
    assert response.accepted_renderer.format == 'json'


@pytest.mark.django_db
def test_jurisdictions(load_parsed_metadata):
    c = Client()
    response = c.get("%s/jurisdictions/?format=json" % settings.API_FULL_URL)
    assert response.status_code == 200
    assert response.accepted_renderer.format == "json"
    jurisdictions = json.loads(response.content)['results']
    assert len(jurisdictions) == 2
    assert jurisdictions[1]["name"] == "New York"


@pytest.mark.django_db
def test_case(load_parsed_metadata):
    c = Client()
    case = CaseMetadata.objects.get(case_id="32044057892259_0001")
    response = c.get("%s/cases/%s/?format=json" % (settings.API_FULL_URL, case.slug))
    assert response.status_code == 200
    assert response.accepted_renderer.format == "json"
    content = json.loads(response.content)
    assert content.get("name_abbreviation") == case.name_abbreviation


@pytest.mark.django_db
def test_court(load_parsed_metadata):
    c = Client()
    response = c.get("%s/courts/?format=json" % settings.API_FULL_URL)
    assert response.status_code == 200
    assert response.accepted_renderer.format == "json"
    results = json.loads(response.content)['results']
    assert len(results) == 2


@pytest.mark.django_db
def test_reporter(load_parsed_metadata):
    c = Client()
    response = c.get("%s/reporters/?format=json" % settings.API_FULL_URL)
    assert response.status_code == 200
    assert response.accepted_renderer.format == "json"
    results = json.loads(response.content)['results']
    assert len(results) == 2
