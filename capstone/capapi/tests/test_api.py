import pytest

from test_data.test_fixtures.factories import *
from capapi.tests.helpers import check_response
from capapi.permissions import casebody_permissions

@pytest.mark.django_db(transaction=True)
def test_api_urls(client, api_url):
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
    jurisdiction_url = content.get("jurisdiction")["url"]
    assert jurisdiction_url
    response = client.get(jurisdiction_url)
    check_response(response)
    content = response.json()
    assert content.get("name") == case.jurisdiction.name


@pytest.mark.django_db(transaction=True)
def test_case_citation_redirect(api_url, client, citation):
    url = "%scases/%s?format=json" % (api_url, citation.normalized_cite)

    # should have received a redirect
    response = client.get(url)
    check_response(response, status_code=301, format='')

    response = client.get(url, follow=True)
    check_response(response, format='json')
    content = response.json()['results']
    case = citation.case
    # should only have one case returned
    assert len(content) == 1
    assert content[0]['id'] == case.id
    # should only have one citation for this case
    assert len(content[0]['citations']) == 1
    assert content[0]['citations'][0]['cite'] == citation.cite

    # allow user to enter real citation (not normalized)
    url = "%scases/%s?format=json" % (api_url, citation.cite)
    response = client.get(url, follow=True)

    check_response(response, format='json')
    content = response.json()['results']
    case = citation.case
    assert len(content) == 1
    assert content[0]['id'] == case.id

    # citation redirect should work with periods in the url, too
    new_citation = CitationFactory(cite='1 Mass. 1', normalized_cite='1-mass-1', case=citation.case)
    new_citation.save()

    url = "%scases/%s?format=json" % (api_url, new_citation.cite)
    response = client.get(url)
    check_response(response, status_code=301, format='')
    response = client.get(url, follow=True)
    check_response(response, format='json')
    content = response.json()['results']
    case = citation.case
    assert len(content) == 1
    assert content[0]['id'] == case.id


@pytest.mark.django_db(transaction=True)
def test_unauthorized_request(api_user, api_url, auth_client, case):
    assert api_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?full_case=true" % (api_url, case.id)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token fake'})
    check_response(response, status_code=401, format='')

    api_user.refresh_from_db()
    assert api_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE


@pytest.mark.django_db(transaction=True)
def test_unauthenticated_full_case(api_url, case, jurisdiction, client):
    """
    we should allow users to get full case without authentication
    if case is whitelisted
    we should allow users to see why they couldn't get full case
    if case is blacklisted
    """
    jurisdiction.whitelisted = True
    jurisdiction.save()
    case.jurisdiction = jurisdiction
    case.save()

    url = "%scases/%s/?format=json&full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='')
    content = response.json()
    assert "casebody" in content

    jurisdiction.whitelisted = False
    jurisdiction.save()
    case.jurisdiction = jurisdiction
    case.save()

    url = "%scases/%s/?format=json&full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='')
    casebody = response.json()['casebody']
    assert 'error_' in casebody['status']
    assert not casebody['data']


@pytest.mark.django_db(transaction=True)
def test_authenticated_full_case(auth_user, api_url, auth_client, jurisdiction, case):
    """
    full cases viewed on whitelisted jurisdictions should not be counted against the user
    """
    jurisdiction.whitelisted = True
    jurisdiction.save()

    case.jurisdiction = jurisdiction
    case.save()

    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    assert response.headers['Content-Type'] == 'text/html; charset=utf-8'

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE

    # if auth_user downloads a mixed case load, their case_allowance_remaining should only reflect the blacklisted cases
    jurisdiction.whitelisted = False
    jurisdiction.save()

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url, headers={'AUTHORIZATION': 'Token {}'.format(auth_user.get_api_key())})
    check_response(response, format='')

    assert response.headers['Content-Type'] == 'text/html; charset=utf-8'

    # make sure the auth_user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 1


@pytest.mark.django_db
def test_case_body_formats(api_url, client, jurisdiction, ingest_case_xml):
    """
    api should return different casebody formats upon request
    """
    jurisdiction.whitelisted = True
    jurisdiction.save()
    case = CaseFactory(jurisdiction=jurisdiction)
    case.save()
    ingest_case_xml.metadata = case
    ingest_case_xml.save()

    # body_format not specified, should get back text
    url = "%scases/%s/?format=json&full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='json')
    content = response.json()
    assert "casebody" in content
    casebody = content["casebody"]
    assert type(casebody) is dict
    assert len(casebody['data']) > 0
    assert casebody['status'] == casebody_permissions[0]
    assert "<" not in casebody['data']

    # getting back xml body
    url = "%scases/%s/?format=json&full_case=true&body_format=xml" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='json')
    content = response.json()
    assert "casebody" in content
    casebody = content["casebody"]
    assert casebody['status'] == "ok"
    assert "<?xml version=" in casebody['data']

    # getting back html body
    url = "%scases/%s/?format=json&full_case=true&body_format=html" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, format='json')
    content = response.json()
    assert "casebody" in content
    casebody = content["casebody"]
    assert casebody['status'] == "ok"
    assert "</h4>" in casebody['data']



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
