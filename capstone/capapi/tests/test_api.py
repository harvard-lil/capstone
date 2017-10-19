import pytest
from django.conf import settings

from capdb.models import CaseMetadata, Jurisdiction
from test_data.factories import *


def check_response(response, status_code=200, format='json'):
    assert response.status_code == status_code
    if format:
        assert response.accepted_renderer.format == format


@pytest.mark.django_db(transaction=True)
def test_api_urls(client, api_url, case):
    response = client.get('%scases/' % api_url)
    check_response(response, format='api')
    response = client.get('%scases/?format=json' % api_url)
    check_response(response)
    response = client.get('%sjurisdictions/' % api_url)
    check_response(response, format='api')
    response = client.get('%sjurisdictions/?format=json' % api_url)
    check_response(response)


@pytest.mark.django_db
def test_jurisdictions(client, api_url, case):
    response = client.get("%sjurisdictions/?format=json" % api_url)
    check_response(response)
    jurisdictions = response.json()['results']
    assert len(jurisdictions) > 0
    assert len(jurisdictions) == Jurisdiction.objects.all().count()


@pytest.mark.django_db
def test_case(client, api_url, case):
    case = CaseMetadata.objects.first()
    response = client.get("%scases/%s/?format=json" % (api_url, case.slug))
    check_response(response)
    content = response.json()
    assert content.get("name_abbreviation") == case.name_abbreviation


@pytest.mark.django_db(transaction=True)
def test_single_case_download(auth_user, api_url, auth_client, case):
    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?type=download" % (api_url, case.slug)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    # assert we've gotten something that looks like a zipped file
    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'
    assert case.slug in response.headers['Content-Disposition']

    # make sure we've subtracted auth_user's case download
    auth_user.refresh_from_db()
    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 1


@pytest.mark.django_db(transaction=True)
def test_many_case_download(auth_user, api_url, auth_client):
    num_created = 3
    # generate 3 cases with the same docket_number
    for case in range(0, num_created):
        setup_case(**{'docket_number': '123'})

    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/?docket_number=123&type=download" % api_url

    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    # assert we've gotten something that looks like a zipped file
    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'

    # make sure we've subtracted user's case download
    auth_user.refresh_from_db()
    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - num_created

@pytest.mark.django_db(transaction=True)
def test_max_number_case_download(auth_user, api_url, auth_client):
    """
    check that user only gets charged for the amount downloaded
    not the amount available in all
    """
    num_to_download = 2
    num_created = 3

    for case in range(0, num_created):
        setup_case(**{'docket_number': '123'})

    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE

    # request download 2 cases
    url = "%scases/?docket_number=123&limit=%s&type=download" % (api_url, num_to_download)

    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    # assert we've gotten something that looks like a zipped file
    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'

    # make sure we've subtracted auth_user's case download
    auth_user.refresh_from_db()
    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 2


@pytest.mark.django_db(transaction=True)
def test_unauthorized_download(user, api_url, auth_client, case):
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?type=download" % (api_url, case.slug)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token fake'})
    check_response(response, status_code=401, format='')

    user.refresh_from_db()
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE


@pytest.mark.django_db(transaction=True)
def test_open_jurisdiction(auth_user, api_url, auth_client):
    """
    cases downloaded from open jurisdictions should not be counted against the user
    """
    jurisdiction = JurisdictionFactory(name='Illinois', whitelisted=True)
    jurisdiction.save()
    common_name = 'Terrible v. Terrible'
    case = setup_case(**{'jurisdiction': jurisdiction,
                         'name': common_name,
                         'slug': slugify(common_name)})

    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?type=download" % (api_url, case.slug)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE

    # if auth_user downloads a mixed case load, their case_allowance should only reflect the blacklisted cases
    jurisdiction = JurisdictionFactory(name='Blocked')
    case = setup_case(**{'jurisdiction': jurisdiction,
                         'name': common_name,
                         'slug': slugify(common_name) + '-1'})

    url = "%scases/?name=%s&type=download" % (api_url, case.name)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    assert type(response.content) is bytes
    assert response.headers['Content-Type'] == 'application/zip'

    # make sure the auth_user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 1


@pytest.mark.django_db
def test_filter_case_by_(api_url, client, case):
    citation = case.citations.all().get(type="official").cite
    response = client.get("%scases/?citation=%s&format=json" % (api_url, citation))
    check_response(response)
    content = response.json()['results']
    assert len(content) == 1
    assert content[0].get("slug") == case.slug


@pytest.mark.django_db
def test_court(api_url, client, court):
    response = client.get("%scourts/?format=json" % api_url)
    check_response(response)
    results = response.json()['results']
    assert len(results) == 1


@pytest.mark.django_db
def test_reporter(api_url, client, reporter):
    response = client.get("%sreporters/?format=json" % api_url)
    check_response(response)
    results = response.json()['results']
    assert len(results) == 1


#  | User views
@pytest.mark.django_db
def test_view_details(auth_user, auth_client):
    """
    User is able to log in successfully and see an API Token
    """
    url = "http://testserver/accounts/view_details/"
    auth_user.set_password('pass')
    response = auth_client.post(url, json={
        'email': auth_user.email,
        'password': 'pass'
    })

    check_response(response, format='')
    assert "user_api_key" in response.text
    assert auth_user.get_api_key() in response.text

    response = auth_client.post(url, {
        'email': auth_user.email,
        'password': 'fake'
    })

    check_response(response, status_code=401, format='')
    assert auth_user.get_api_key() not in response.text
