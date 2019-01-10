import json

import pytest

from capweb.helpers import reverse
from capapi.tests.helpers import check_response


@pytest.mark.django_db
def test_search_jurisdiction_list(client, ingest_case_xml):
    response = client.get(reverse('jurisdiction_list'))
    check_response(response, content_type="application/json")
    decoded = json.loads(response.content.decode())
    assert decoded['315'] == 'Ill. App.- Illinois Appellate Court Reports'
    assert len(decoded) > 1


@pytest.mark.django_db
def test_search_reporter_list(client, ingest_case_xml):
    response = client.get(reverse('reporter_list'))
    check_response(response, content_type="application/json")
    decoded = json.loads(response.content.decode())
    assert decoded['477'] == 'Wash. App.- Washington Appellate Reports'
    assert len(decoded) > 1


@pytest.mark.django_db
def test_search_court_list(client, ingest_case_xml):
    response = client.get(reverse('court_list'))
    check_response(response, content_type="application/json")
    decoded = json.loads(response.content.decode())
    assert decoded['ill-app-ct'] == 'Illinois: Illinois Appellate Court'
    assert len(decoded) > 1