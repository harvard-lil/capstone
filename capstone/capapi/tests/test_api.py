import pytest

from django.test import Client
from django.conf import settings

from rest_framework.test import RequestsClient

from capdb.models import CaseMetadata, Jurisdiction

from test_data.factories import *


def check_response(response, status_code=200, format='json'):
    assert response.status_code == status_code
    if format:
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

    case = setup_case()
    response = c.get("%s/cases/%s/?format=json" % (settings.API_FULL_URL, case.slug))
    check_response(response)
    content = response.json()
    assert content.get("name_abbreviation") == case.name_abbreviation


@pytest.mark.django_db(transaction=True)
def test_single_case_download():
    user = setup_authenticated_user()
    client = RequestsClient()

    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    case = setup_case()
    url = "http://testserver%s/cases/%s/?type=download" % (settings.API_FULL_URL, case.slug)
    response = client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(user.get_api_key())})
    check_response(response, format='')

    # assert we've gotten something that looks like a zipped file
    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'
    assert case.slug in response.headers['Content-Disposition']

    # make sure we've subtracted user's case download
    user.refresh_from_db()
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 1


@pytest.mark.django_db(transaction=True)
def test_many_case_download():
    user = setup_authenticated_user()
    client = RequestsClient()

    num_of_cases_to_create = 3
    # generate four cases with the same docket_number
    for case in range(0, num_of_cases_to_create):
        setup_case(**{'docket_number': '123'})

    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    url = "http://testserver%s/cases/?docket_number=123&type=download" % settings.API_FULL_URL

    response = client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(user.get_api_key())})
    check_response(response, format='')

    # assert we've gotten something that looks like a zipped file
    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'

    # make sure we've subtracted user's case download
    user.refresh_from_db()
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - num_of_cases_to_create


@pytest.mark.django_db(transaction=True)
def test_unauthorized_download():
    user = APIUserFactory.create()

    client = RequestsClient()

    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    case = setup_case()
    url = "http://testserver%s/cases/%s/?type=download" % (settings.API_FULL_URL, case.slug)
    response = client.get(url, headers={'AUTHORIZATION': 'Token fake'})
    check_response(response, status_code=401, format='')

    user.refresh_from_db()
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE


@pytest.mark.django_db(transaction=True)
def test_open_jurisdiction():
    """
    cases downloaded from open jurisdictions should not be counted against the user
    """
    user = setup_authenticated_user()
    client = RequestsClient()
    jurisdiction = JurisdictionFactory(name='Illinois')
    jurisdiction.save()
    common_name = 'Terrible v. Terrible'
    case = setup_case(**{'jurisdiction': jurisdiction,
                         'name': common_name,
                         'slug': slugify(common_name)})

    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    url = "http://testserver%s/cases/%s/?type=download" % (settings.API_FULL_URL, case.slug)
    response = client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(user.get_api_key())})
    check_response(response, format='')

    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'

    # make sure the user's case download number has remained the same
    user.refresh_from_db()
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE

    # if user downloads a mixed case load, their case_allowance should only reflect the blacklisted cases
    jurisdiction = JurisdictionFactory(name='Blocked')
    case = setup_case(**{'jurisdiction': jurisdiction,
                         'name': common_name,
                         'slug': slugify(common_name) + '-1'})

    url = "http://testserver%s/cases/?name=%s&type=download" % (settings.API_FULL_URL, case.name)
    response = client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(user.get_api_key())})
    check_response(response, format='')
    print(response.headers)

    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'

    # make sure the user's case download number has remained the same
    user.refresh_from_db()
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 1

@pytest.mark.django_db
def test_filter_case_by_citation(load_parsed_metadata):
    c = Client()
    case = CaseMetadata.objects.get(case_id="32044057892259_0001")
    citation = case.citations.all().get(type="official").cite
    response = c.get("%s/cases/?citation=%s&format=json" % (settings.API_FULL_URL, citation))
    check_response(response)
    content = response.json()['results']
    assert len(content) == 1
    assert content[0].get("slug") == case.slug


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


#  | User views
@pytest.mark.django_db
def test_view_details():
    """
    User is able to log in successfully and see an API Token
    """
    user = setup_authenticated_user()
    client = RequestsClient()

    url = "http://testserver/accounts/view_details/"
    response = client.post(url, {
        'email': user.email,
        'password': 'pass'
    })

    check_response(response, format='')
    assert "user_api_key" in response.text
    assert user.get_api_key() in response.text

    response = client.post(url, {
        'email': user.email,
        'password': 'fake'
    })

    check_response(response, status_code=401, format='')
    assert user.get_api_key() not in response.text
