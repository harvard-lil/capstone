import pytest

from django.test import Client
from django.conf import settings

from capdb.models import CaseMetadata, Jurisdiction


def check_response(response, status_code=200, format='json'):
    assert response.status_code == status_code
    assert response.accepted_renderer.format == format

@pytest.mark.django_db
def test_api_urls(load_parsed_metadata):
    c = Client()
    response = c.get('%s/cases/' % settings.API_FULL_URL)
    check_response(response, format='api')
    response = c.get('%s/cases/?format=json' % settings.API_FULL_URL)
    check_response(response)
    response = c.get('%s/jurisdictions/' % settings.API_FULL_URL)
    check_response(response, format='api')
    response = c.get('%s/jurisdictions/?format=json' % settings.API_FULL_URL)
    check_response(response)


@pytest.mark.django_db
def test_jurisdictions(load_parsed_metadata):
    c = Client()
    response = c.get("%s/jurisdictions/?format=json" % settings.API_FULL_URL)
    check_response(response)
    jurisdictions = response.json()['results']
    assert len(jurisdictions) == Jurisdiction.objects.all().count()


@pytest.mark.django_db
def test_case(load_parsed_metadata):
    c = Client()
    case = CaseMetadata.objects.get(case_id="32044057892259_0001")
    response = c.get("%s/cases/%s/?format=json" % (settings.API_FULL_URL, case.slug))
    check_response(response)
    content = response.json()
    assert content.get("name_abbreviation") == case.name_abbreviation


@pytest.mark.django_db
def test_court(load_parsed_metadata):
    c = Client()
    response = c.get("%s/courts/?format=json" % settings.API_FULL_URL)
    check_response(response)
    results = response.json()['results']
    assert len(results) == 2


@pytest.mark.django_db
def test_reporter(load_parsed_metadata):
    c = Client()
    response = c.get("%s/reporters/?format=json" % settings.API_FULL_URL)
    check_response(response)
    results = response.json()['results']
    assert len(results) == 2
