import pytest
from rest_framework.reverse import reverse

from test_data.test_fixtures.factories import *
from capapi.tests.helpers import check_response
from capapi.permissions import casebody_permissions


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


# RESOURCE ENDPOINTS
@pytest.mark.django_db
def test_jurisdictions(client, api_url, case):
    response = client.get("%sjurisdictions/?format=json" % api_url)
    check_response(response)
    jurisdictions = response.json()['results']
    assert len(jurisdictions) > 0
    assert len(jurisdictions) == Jurisdiction.objects.count()


@pytest.mark.django_db
def test_single_jurisdiction(client, api_url, jurisdiction):
    response = client.get("%sjurisdictions/%s/?format=json" % (api_url, jurisdiction.slug))
    check_response(response)
    jur_result = response.json()
    assert len(jur_result) > 1
    print(jur_result)
    assert jur_result['name_long'] == jurisdiction.name_long


@pytest.mark.django_db
def test_courts(api_url, client, court):
    response = client.get("%scourts/?format=json" % api_url)
    check_response(response)
    courts = response.json()['results']
    assert len(courts) > 0
    assert len(courts) == Court.objects.count()


@pytest.mark.django_db
def test_single_court(api_url, client, court):
    court.slug = "unique-slug"
    court.save()
    response = client.get("%scourts/%s/?format=json" % (api_url, court.slug))
    check_response(response)
    court_result = response.json()
    assert court_result['name'] == court.name


@pytest.mark.django_db
def test_cases(client, api_url, case):
    response = client.get("%scases/?format=json" % api_url)
    check_response(response)
    cases = response.json()['results']
    assert len(cases) > 0
    assert len(cases) == CaseMetadata.objects.count()


@pytest.mark.django_db
def test_single_case(client, api_url, case):
    response = client.get("%scases/%s/?format=json" % (api_url, case.pk))
    check_response(response)
    content = response.json()
    assert content.get("name_abbreviation") == case.name_abbreviation


@pytest.mark.django_db
def test_reporters(client, api_url, reporter):
    response = client.get("%sreporters/?format=json" % api_url)
    check_response(response)
    reporters = response.json()['results']
    assert len(reporters) > 0
    assert len(reporters) == Reporter.objects.count()


@pytest.mark.django_db
def test_single_reporter(client, api_url, reporter):
    response = client.get("%sreporters/%s/?format=json" % (api_url, reporter.pk))
    check_response(response)
    content = response.json()
    assert content.get("full_name") == reporter.full_name


# REQUEST AUTHORIZATION
@pytest.mark.django_db
def test_unauthorized_request(api_user, api_url, client, case):
    assert api_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE
    url = "%scases/%s/?full_case=true" % (api_url, case.id)
    client.credentials(HTTP_AUTHORIZATION='Token fake')
    response = client.get(url)
    check_response(response, status_code=401, format='')

    api_user.refresh_from_db()
    assert api_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_authenticated_full_case_whitelisted(auth_user, api_url, auth_client, case):
    ### whitelisted jurisdiction should not be counted against the user

    case.jurisdiction.whitelisted = True
    case.jurisdiction.save()

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url)
    check_response(response, format='')

    assert response['Content-Type'] == 'text/html; charset=utf-8'

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE

@pytest.mark.django_db
def test_authenticated_full_case_blacklisted(auth_user, api_url, auth_client, case):
    ### blacklisted jurisdiction cases should be counted against the user

    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url)
    check_response(response, format='')

    assert response['Content-Type'] == 'text/html; charset=utf-8'

    # make sure the auth_user's case download number has gone down by 1
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 1

@pytest.mark.django_db
def test_authenticated_multiple_full_cases(auth_user, api_url, auth_client, three_cases, jurisdiction, django_assert_num_queries):
    ### mixed requests should be counted only for blacklisted cases

    # one whitelisted case
    three_cases[0].jurisdiction.whitelisted = True
    three_cases[0].jurisdiction.save()

    # two blacklisted cases
    jurisdiction.whitelisted = False
    jurisdiction.save()
    for extra_case in three_cases[1:]:
        extra_case.jurisdiction = jurisdiction
        extra_case.save()

    url = "%scases/?full_case=true" % (api_url)
    with django_assert_num_queries(select=7, update=1):
        response = auth_client.get(url)
    check_response(response, format='')
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    # make sure the auth_user's case download number has gone down by 2
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 2


@pytest.mark.django_db
def test_authentication_as_query_param(auth_user, api_url, client, jurisdiction, case):
    """
    Allow the user to pass api key as query parameter
    """
    jurisdiction.whitelisted = False
    jurisdiction.save()
    case.jurisdiction = jurisdiction
    case.save()

    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE
    token = auth_user.get_api_key()
    url = "%scases/%s/?full_case=true&api_key=%s&format=json" % (api_url, case.pk, token)
    response = client.get(url)
    check_response(response, format='')
    auth_user.refresh_from_db()

    content = response.json()
    assert "casebody" in content
    casebody = content["casebody"]
    assert casebody['status'] == "ok"

    assert auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 1


# CITATION REDIRECTS
@pytest.mark.django_db
def test_case_citation_redirect(api_url, client, citation):
    """Should allow various forms of citation, should redirect to normalized_cite"""
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
    citations_result = content[0]['citations']
    assert len(citations_result) == 1
    assert citations_result[0]['cite'] == citation.cite

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


# FORMATS
@pytest.mark.django_db
def test_case_body_formats(api_url, client, case):
    """
    api should return different casebody formats upon request
    """
    case.jurisdiction.whitelisted = True
    case.jurisdiction.save()

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


# FILTERING
@pytest.mark.django_db
def test_filter_case(api_url, client, three_cases, court, jurisdiction):
    # filtering case by court
    case_to_test = three_cases[2]
    case_to_test.court = court
    case_to_test.save()

    response = client.get("%scases/?court_name=%s&format=json" % (api_url, three_cases[2].court.name))
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by name_abbreviation
    case_to_test = three_cases[0]
    case_to_test.name_abbreviation = "Bill v. Bob"
    case_to_test.save()
    assert case_to_test.name_abbreviation != three_cases[1].name_abbreviation
    response = client.get("%scases/?name_abbreviation=%s&format=json" % (api_url, case_to_test.name_abbreviation))
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by name_abbreviation lowercased substring
    assert case_to_test.name_abbreviation != three_cases[1].name_abbreviation
    response = client.get("%scases/?name_abbreviation=%s&format=json" % (api_url, "bill"))
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by court substring
    case_to_test = three_cases[2]
    court_name = case_to_test.court.name.split(' ')[1]
    response = client.get("%scases/?court_name=%s&format=json" % (api_url, court_name))
    content = response.json()
    for result in content['results']:
        assert result['court'] == case_to_test.court.name

    # filtering case by reporter substring
    reporter_name = case_to_test.reporter.full_name.split(' ')[1]
    response = client.get("%scases/?reporter_name=%s&format=json" % (api_url, reporter_name))
    content = response.json()
    for result in content['results']:
        assert result['reporter'] == case_to_test.reporter.full_name


@pytest.mark.django_db
def test_filter_court(api_url, client, court):
    # filtering court by jurisdiction
    jur_slug = court.jurisdiction.slug
    response = client.get("%scourts/?jurisdiction_slug=%s&format=json" % (api_url, jur_slug))
    check_response(response)
    results = response.json()['results']
    assert court.name_abbreviation == results[0]['name_abbreviation']

    # filtering court by name substring
    court_name_str = court.name.split(' ')[1]
    response = client.get("%scourts/?name=%s&format=json" % (api_url, court_name_str))
    content = response.json()
    for result in content['results']:
        assert court_name_str in result['name']


@pytest.mark.django_db
def test_filter_reporter(api_url, client, reporter):
    # filtering reporter by name substring
    reporter_name_str = reporter.full_name.split(' ')[1]
    response = client.get("%sreporters/?full_name=%s&format=json" % (api_url, reporter_name_str))
    content = response.json()
    for result in content['results']:
        assert reporter_name_str in result['full_name']


#  USER VIEWS
@pytest.mark.django_db
def test_view_details(auth_user, client):
    """
    User is able to log in successfully and see an API Token
    """
    url = reverse('apiuser-view-details')
    auth_user.set_password('pass')
    auth_user.save()
    response = client.post(url, {
        'email': auth_user.email,
        'password': 'pass'
    }, format='json')

    check_response(response, format='')
    assert b"user_api_key" in response.content
    assert auth_user.get_api_key() in response.content.decode()

    response = client.post(url, {
        'email': auth_user.email,
        'password': 'fake'
    }, format='json')

    check_response(response, status_code=401, format='')
    assert auth_user.get_api_key() not in response.content.decode()
