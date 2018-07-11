import pytest
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from test_data.test_fixtures.factories import *
from scripts.process_metadata import parse_decision_date
from capapi.tests.helpers import check_response
from capapi.permissions import casebody_permissions


@pytest.mark.django_db
def test_flow(client, api_url, case):
    """user should be able to click through to get to different tables"""
    # start with case
    response = client.get("%scases/%s/" % (api_url, case.pk))
    check_response(response)
    content = response.json()
    # onwards to court
    court_url = content.get("court")["url"]
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


@pytest.mark.django_db
def test_jurisdiction_redirect(api_url, client, case, jurisdiction):
    jurisdiction.name = 'Neb.'
    jurisdiction.slug = 'neb'
    jurisdiction.save()
    case.jurisdiction = jurisdiction
    case.save()

    response = client.get("%scases/?jurisdiction=%s" % (api_url, jurisdiction.name), follow=True)
    query_string = response.request.get('QUERY_STRING')
    query, jurisdiction_name = query_string.split('=')
    assert jurisdiction_name == jurisdiction.slug


# RESOURCE ENDPOINTS
@pytest.mark.django_db
def test_jurisdictions(client, api_url, case):
    response = client.get("%sjurisdictions/" % api_url)
    check_response(response)
    jurisdictions = response.json()['results']
    assert len(jurisdictions) > 0
    assert len(jurisdictions) == Jurisdiction.objects.count()


@pytest.mark.django_db
def test_single_jurisdiction(client, api_url, jurisdiction):
    response = client.get("%sjurisdictions/%s/" % (api_url, jurisdiction.slug))
    check_response(response)
    jur_result = response.json()
    assert len(jur_result) > 1
    print(jur_result)
    assert jur_result['name_long'] == jurisdiction.name_long


@pytest.mark.django_db
def test_courts(api_url, client, court):
    response = client.get("%scourts/" % api_url)
    check_response(response)
    courts = response.json()['results']
    assert len(courts) > 0
    assert len(courts) == Court.objects.count()


@pytest.mark.django_db
def test_single_court(api_url, client, court):
    court.slug = "unique-slug"
    court.save()
    response = client.get("%scourts/%s/" % (api_url, court.slug))
    check_response(response)
    court_result = response.json()
    assert court_result['name'] == court.name


@pytest.mark.django_db
def test_cases(client, api_url, case):
    response = client.get("%scases/" % api_url)
    check_response(response)
    cases = response.json()['results']
    assert len(cases) > 0
    assert len(cases) == CaseMetadata.objects.count()


@pytest.mark.django_db
def test_single_case(client, api_url, case):
    response = client.get("%scases/%s/" % (api_url, case.pk))
    check_response(response)
    content = response.json()
    assert content.get("name_abbreviation") == case.name_abbreviation


@pytest.mark.django_db
def test_cases_count_cache(client, three_cases, django_assert_num_queries):
    # fetching same endpoing a second time should have one less query, because queryset.count() is cached
    with django_assert_num_queries(select=3):
        response = client.get(reverse('casemetadata-list'))
        assert response.json()['count'] == 3
    with django_assert_num_queries(select=2):
        response = client.get(reverse('casemetadata-list'))
        assert response.json()['count'] == 3

@pytest.mark.django_db
def test_reporters(client, api_url, reporter):
    response = client.get("%sreporters/" % api_url)
    check_response(response)
    reporters = response.json()['results']
    assert len(reporters) > 0
    assert len(reporters) == Reporter.objects.count()


@pytest.mark.django_db
def test_single_reporter(client, api_url, reporter):
    response = client.get("%sreporters/%s/" % (api_url, reporter.pk))
    check_response(response)
    content = response.json()
    assert content.get("full_name") == reporter.full_name


# REQUEST AUTHORIZATION
@pytest.mark.django_db
def test_unauthorized_request(cap_user, api_url, client, case):
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance
    url = "%scases/%s/?full_case=true" % (api_url, case.id)
    client.credentials(HTTP_AUTHORIZATION='Token fake')
    response = client.get(url)
    check_response(response, status_code=401)

    cap_user.refresh_from_db()
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance


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

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response)
    content = response.json()
    assert "casebody" in content

    if case.judges:
        judges = content['casebody']['judges']
        assert len(judges)
    if case.attorneys:
        attorneys = content['casebody']['attorneys']
        assert len(attorneys)
    if case.parties:
        parties = content['casebody']['parties']
        assert len(parties)
    if case.opinions:
        opinions = content['casebody']['opinions']
        assert len(opinions)

    jurisdiction.whitelisted = False
    jurisdiction.save()
    case.jurisdiction = jurisdiction
    case.save()

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response)
    content = response.json()
    casebody = content['casebody']
    assert 'error_' in casebody['status']
    assert not casebody['data']
    if case.judges:
        assert 'judges' not in casebody
    if case.attorneys:
        assert 'attorneys' not in casebody
    if case.parties:
        assert 'parties' not in casebody
    if case.opinions:
        assert 'opinions' not in casebody

    url = "%scases/%s/?format=xml&full_case=true" % (api_url, case.pk)
    response = client.get(url)

    check_response(response, content_type="application/xml", content_includes='error_auth_required')

    url = "%scases/%s/?format=html&full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response, content_type="text/html", content_includes='<h1>Error: Not Authenticated')


@pytest.mark.django_db
def test_authenticated_full_case_whitelisted(auth_user, api_url, auth_client, case):
    ### whitelisted jurisdiction should not be counted against the user

    case.jurisdiction.whitelisted = True
    case.jurisdiction.save()

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url)
    check_response(response)
    result = response.json()
    casebody = result['casebody']
    assert casebody['status'] == 'ok'
    assert 'judges' in casebody
    assert 'attorneys' in casebody
    assert 'parties' in casebody
    assert 'opinions' in casebody

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance


@pytest.mark.django_db
def test_authenticated_full_case_blacklisted(auth_user, api_url, auth_client, case):
    ### blacklisted jurisdiction cases should be counted against the user

    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url)
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # make sure the auth_user's case download number has gone down by 1
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 1


@pytest.mark.django_db
def test_unlimited_access(auth_user, api_url, auth_client, case):
    ### user with unlimited access should not have blacklisted cases count against them
    auth_user.total_case_allowance = 500
    auth_user.unlimited_access_until = timedelta(hours=24) + timezone.now()
    auth_user.save()
    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()

    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url)
    check_response(response)
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance

    # total_case_allowance shouldn't matter if unlimited access is in effect
    auth_user.total_case_allowance = 0
    auth_user.case_allowance_remaining = 0
    auth_user.save()
    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url)
    check_response(response)
    result = response.json()
    casebody = result['casebody']
    assert casebody['status'] == 'ok'
    assert 'judges' in casebody
    assert 'attorneys' in casebody
    assert 'parties' in casebody
    assert 'opinions' in casebody

    # don't allow user to download blacklisted case if unlimited access has expired
    # and they don't have enough case allowance
    auth_user.total_case_allowance = 0
    auth_user.case_allowance_remaining = 0
    auth_user.unlimited_access_until = timezone.now() - timedelta(hours=1)
    auth_user.save()
    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = auth_client.get(url)
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] != 'ok'


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
    # preload capapi.filters.jur_choices so it doesn't sometimes get counted by django_assert_num_queries below
    from capapi.filters import jur_choices
    len(jur_choices)

    # fetch the two blacklisted cases and one whitelisted case
    url = "%scases/?full_case=true" % (api_url)
    with django_assert_num_queries(select=3):
        response = auth_client.get(url)
    check_response(response)
    # make sure the auth_user's case download number has gone down by 2
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 2


# CITATION REDIRECTS
@pytest.mark.django_db
def test_case_citation_redirect(api_url, client, citation):
    """Should allow various forms of citation, should redirect to normalized_cite"""
    url = "%scases/%s" % (api_url, citation.normalized_cite)

    # should have received a redirect
    response = client.get(url)
    check_response(response, status_code=301)

    response = client.get(url, follow=True)
    check_response(response)
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
    url = "%scases/%s" % (api_url, citation.cite)
    response = client.get(url, follow=True)

    check_response(response)
    content = response.json()['results']
    case = citation.case
    assert len(content) == 1
    assert content[0]['id'] == case.id

    # citation redirect should work with periods in the url, too
    new_citation = CitationFactory(cite='1 Mass. 1', normalized_cite='1-mass-1', case=citation.case)
    new_citation.save()

    url = "%scases/%s" % (api_url, new_citation.cite)
    response = client.get(url)
    check_response(response, status_code=301)
    response = client.get(url, follow=True)
    check_response(response)
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
    url = "%scases/%s/?full_case=true" % (api_url, case.pk)
    response = client.get(url)
    check_response(response)
    content = response.json()
    assert "casebody" in content
    casebody = content["casebody"]
    assert type(casebody) is dict
    assert len(casebody['data']) > 0
    assert casebody['status'] == casebody_permissions[0]
    assert "<" not in casebody['data']

    # getting back xml body
    url = "%scases/%s/?full_case=true&body_format=xml" % (api_url, case.pk)
    response = client.get(url)
    check_response(response)
    content = response.json()
    assert "casebody" in content
    casebody = content["casebody"]
    assert casebody['status'] == "ok"
    assert "<?xml version=" in casebody['data']

    # getting back html body
    url = "%scases/%s/?full_case=true&body_format=html" % (api_url, case.pk)
    response = client.get(url)
    check_response(response)
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

    # filtering case by name_abbreviation
    case_to_test = three_cases[0]
    case_to_test.name_abbreviation = "Bill v. Bob"
    case_to_test.save()
    assert case_to_test.name_abbreviation != three_cases[1].name_abbreviation
    response = client.get("%scases/?name_abbreviation=%s" % (api_url, case_to_test.name_abbreviation))
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by name_abbreviation lowercased substring
    assert case_to_test.name_abbreviation != three_cases[1].name_abbreviation
    response = client.get("%scases/?name_abbreviation=%s" % (api_url, "bill"))
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by court substring
    case_to_test = three_cases[2]
    court = case_to_test.court
    response = client.get("%scases/?court=%s" % (api_url, court.slug))
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by reporter
    reporter = case_to_test.reporter
    response = client.get("%scases/?reporter=%s" % (api_url, reporter.pk))
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering by decision_date
    # make sure that we can filter by decision_date's datefield
    # but we get decision_date_original string in response
    case_to_test = three_cases[0]
    case_to_test.decision_date_original = "1988"
    case_to_test.decision_date = parse_decision_date(case_to_test.decision_date_original)
    case_to_test.save()
    response = client.get("%scases/?decision_date_min=%s&decision_date_max=%s" % (api_url, "1987-12-30", "1988-01-02"))
    content = response.json()
    result = content['results'][0]
    assert case_to_test.decision_date_original == result['decision_date']

    # by jurisdiction
    case_to_test = three_cases[0]
    jurisdiction.name = 'Neb.'
    jurisdiction.slug = 'neb'
    jurisdiction.save()
    case_to_test.jurisdiction = jurisdiction
    case_to_test.save()

    response = client.get("%scases/?jurisdiction=%s" % (api_url, jurisdiction.name), follow=True)
    content = response.json()
    result = content['results'][0]
    assert case_to_test.jurisdiction.slug == result['jurisdiction']['slug']

    # by docket_number
    case_to_test = three_cases[0]
    case_to_test.docket_number = "NUMBER 13-16-00273-CV"
    case_to_test.save()
    response = client.get("%scases/?docket_number=%s" % (api_url, "13-16-00273"), follow=True)
    content = response.json()
    result = content['results'][0]
    assert case_to_test.docket_number== result['docket_number']


@pytest.mark.django_db
def test_filter_court(api_url, client, court):
    # filtering court by jurisdiction
    jur_slug = court.jurisdiction.slug
    response = client.get("%scourts/?jurisdiction_slug=%s" % (api_url, jur_slug))
    check_response(response)
    results = response.json()['results']
    assert court.name_abbreviation == results[0]['name_abbreviation']

    # filtering court by name substring
    court_name_str = court.name.split(' ')[1]
    response = client.get("%scourts/?name=%s" % (api_url, court_name_str))
    content = response.json()
    for result in content['results']:
        assert court_name_str in result['name']


@pytest.mark.django_db
def test_filter_reporter(api_url, client, reporter):
    # filtering reporter by name substring
    reporter_name_str = reporter.full_name.split(' ')[1]
    response = client.get("%sreporters/?full_name=%s" % (api_url, reporter_name_str))
    content = response.json()
    for result in content['results']:
        assert reporter_name_str in result['full_name']


# RESPONSE FORMATS
@pytest.mark.django_db
def test_formats(api_url, client, auth_client, case):
    formats = [
        ('html', 'text/html'),
        ('xml', 'application/xml'),
        ('json', 'application/json'),
    ]
    for format, content_type in formats:
        # test format html without api_key
        url = "%scases/%s/?format=%s&full_case=true" % (api_url, case.id, format)
        response = client.get(url)
        check_response(response, content_type=content_type)
        response_content = response.content.decode()
        assert 'error' in response_content.lower()

        # test full, authorized case
        url = "%scases/%s/?format=%s&full_case=true" % (api_url, case.id, format)
        response = auth_client.get(url)
        check_response(response, content_type=content_type, content_includes=case.name)


# API SPECIFICATION ENDPOINTS
@pytest.mark.django_db
def test_swagger(client):
    routes = [
        ('/', 'text/html'),
        ('.json', 'application/json'),
        ('.yaml', 'application/yaml'),
    ]
    for route, content_type in routes:
        response = client.get("/swagger%s" % route)
        check_response(response, content_type=content_type)


@pytest.mark.django_db
def test_redoc(client):
    response = client.get("/redoc/")
    check_response(response, content_type="text/html")
