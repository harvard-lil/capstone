import pytest

from test_data.test_fixtures.factories import *
from capapi.tests.helpers import check_response

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
def test_jurisdiction(client, api_url, jurisdiction):
    response = client.get("%sjurisdictions/%s/?format=json" % (api_url, jurisdiction.slug))
    check_response(response)


@pytest.mark.django_db
def test_case(client, api_url, case):
    response = client.get("%scases/%s/?format=json" % (api_url, case.pk))
    check_response(response)
    content = response.json()
    assert content.get("name_abbreviation") == case.name_abbreviation


@pytest.mark.django_db
def test_flow(client, api_url, case):
    """user should be able to click through to get to different tables"""
    # start with case
    response = client.get("%scases/%s/?format=json" % (api_url, case.pk))
    check_response(response)
    content = response.json()
    # onwards to court
    court_url = content.get("court_url")
    assert court_url
    response = client.get(court_url)
    check_response(response)
    # onwards to jurisdiction
    jurisdiction_url = content.get("jurisdiction_url")
    assert jurisdiction_url
    response = client.get(jurisdiction_url)
    check_response(response)
    content = response.json()
    assert content.get("name") == case.jurisdiction.name


@pytest.mark.django_db(transaction=True)
def test_case_citation_redirect(auth_user, api_url, client, citation):
    # citation = case.citation.get(type='official')

    url = "%scases/%s?format=json" % (api_url, citation.normalized_cite)
    print('getting url:', url, citation.normalized_cite)

    # should have received a redirect
    response = client.get(url)
    check_response(response, status_code=301, format='')

    response = client.get(url, follow=True)
    check_response(response)
    content = response.json()['results']
    case = citation.case
    # should only have one case returned
    assert len(content) == 1
    assert content[0]['id'] == case.id
    # should only have one citation for this case
    assert len(content[0]['citations']) == 1
    assert content[0]['citations'][0]['cite'] == citation.cite


@pytest.mark.django_db(transaction=True)
def test_unauthorized_request(user, api_url, auth_client, case):
    assert user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?full_case=true" % (api_url, case.id)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token fake'})
    check_response(response, status_code=401, format='')

    user.refresh_from_db()
    assert user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE


@pytest.mark.django_db(transaction=True)
def test_unauthenticated_full_case(user, api_url, client):
    """
    we should allow users to get full case without authentication
    if case is whitelisted
    """
    jurisdiction = JurisdictionFactory(name='Illinois', whitelisted=True)
    jurisdiction.save()
    case = setup_case(**{'jurisdiction': jurisdiction})

    url = "%scases/%s/?format=json&full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='')
    content = response.json()
    assert "casebody" in content

    jurisdiction = JurisdictionFactory(name='New York', whitelisted=False)
    jurisdiction.save()
    case = setup_case(**{'jurisdiction': jurisdiction})

    url = "%scases/%s/?format=json&full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='', status_code=401)


@pytest.mark.django_db(transaction=True)
def test_authenticated_full_case(auth_user, api_url, auth_client):
    """
    full cases viewed on whitelisted jurisdictions should not be counted against the user
    """
    jurisdiction = JurisdictionFactory(name='Illinois', whitelisted=True)
    jurisdiction.save()
    common_name = 'Terrible v. Terrible'
    case = setup_case(**{'jurisdiction': jurisdiction,
                         'name': common_name})

    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    assert response.headers['Content-Type'] == 'text/html; charset=utf-8'

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE

    # if auth_user downloads a mixed case load, their case_allowance_remaining should only reflect the blacklisted cases
    jurisdiction = JurisdictionFactory(name='Blocked', whitelisted=False)
    case = setup_case(**{'jurisdiction': jurisdiction})

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    assert response.headers['Content-Type'] == 'text/html; charset=utf-8'

    # make sure the auth_user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 1


@pytest.mark.django_db
def test_full_case_formats(api_url, client, case):
    """
    api should return different casebody formats upon request
    """
    jurisdiction = JurisdictionFactory(name='Illinois', whitelisted=True)
    jurisdiction.save()
    case = setup_case(**{'jurisdiction': jurisdiction})

    # test body_format not specified
    url = "%scases/%s/?format=json&full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='json')
    content = response.json()
    assert "casebody" in content
    assert type(content["casebody"]) is str


@pytest.mark.django_db
def test_filter_case_by_(api_url, client, case):
    cases = []
    for case in range(0, 3):
        cases.append(setup_case())

    # check how many cases exist in a specific court
    court_slug_to_test = cases[2].court.slug
    case_id_to_test = cases[2].id
    case_num = Court.objects.filter(slug=court_slug_to_test).count()

    response = client.get("%scases/?court_slug=%s&format=json" % (api_url, cases[2].court.slug))
    content = response.json()
    # assert only the right case number is returned for court
    assert content['count'] == case_num

    ids = []
    for result in content['results']:
        ids.append(result['id'])

    assert case_id_to_test in ids


@pytest.mark.django_db
def test_court(api_url, client, court):
    response = client.get("%scourts/?format=json" % api_url)
    check_response(response)
    results = response.json()['results']
    assert len(results) == 1


@pytest.mark.django_db
def test_filter_court(api_url, client, court):
    jur_slug = court.jurisdiction.slug
    response = client.get("%scourts/?jurisdiction_slug=%s&format=json" % (api_url, jur_slug))
    check_response(response)
    results = response.json()['results']
    assert court.name_abbreviation == results[0]['name_abbreviation']


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
