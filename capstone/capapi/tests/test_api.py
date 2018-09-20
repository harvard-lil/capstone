import pytest

from capapi import api_reverse
from test_data.test_fixtures.factories import *
from scripts.process_metadata import parse_decision_date
from capapi.tests.helpers import check_response

@pytest.mark.django_db
def test_flow(client, case):
    """user should be able to click through to get to different tables"""
    # start with case
    response = client.get(api_reverse("casemetadata-detail", args=[case.pk]))
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
def test_jurisdiction_redirect(client, case, jurisdiction):
    jurisdiction.name = 'Neb.'
    jurisdiction.slug = 'neb'
    jurisdiction.save()
    case.jurisdiction = jurisdiction
    case.save()

    response = client.get(api_reverse("casemetadata-list"), {"jurisdiction": jurisdiction.name}, follow=True)
    query_string = response.request.get('QUERY_STRING')
    query, jurisdiction_name = query_string.split('=')
    assert jurisdiction_name == jurisdiction.slug


# RESOURCE ENDPOINTS
@pytest.mark.django_db
@pytest.mark.parametrize("fixture_name, detail_attr, comparison_attr", [
    ("jurisdiction", "slug", "name_long"),
    ("court", "slug", "name"),
    ("case", "pk", "name_abbreviation"),
    ("reporter", "pk", "full_name"),
    ("volume_metadata", "pk", "title"),
    ("case_export", "pk", "file_name"),
])
def test_model_endpoint(request, client, fixture_name, detail_attr, comparison_attr):
    """ Generic test to kick the tires on -list and -detail for model endpoints. """
    instance = request.getfuncargvalue(fixture_name)
    model = instance.__class__
    resource_name = model.__name__.lower()

    # test list endpoint
    response = client.get(api_reverse("%s-list" % resource_name))
    check_response(response)
    results = response.json()['results']
    assert results
    assert len(results) == model.objects.count()

    # test detail endpoint
    response = client.get(api_reverse("%s-detail" % resource_name, args=[getattr(instance, detail_attr)]))
    check_response(response)
    results = response.json()
    assert results[comparison_attr] == getattr(instance, comparison_attr)

@pytest.mark.django_db
def test_cases_count_cache(client, three_cases, django_assert_num_queries):
    # fetching same endpoing a second time should have one less query, because queryset.count() is cached
    with django_assert_num_queries(select=3):
        response = client.get(api_reverse('casemetadata-list'))
        assert response.json()['count'] == 3
    with django_assert_num_queries(select=2):
        response = client.get(api_reverse('casemetadata-list'))
        assert response.json()['count'] == 3


# REQUEST AUTHORIZATION
@pytest.mark.django_db
def test_unauthorized_request(cap_user, client, case):
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance
    client.credentials(HTTP_AUTHORIZATION='Token fake')
    response = client.get(api_reverse("casemetadata-detail", args=[case.id]), {"full_case": "true"})
    check_response(response, status_code=401)

    cap_user.refresh_from_db()
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance


@pytest.mark.django_db
def test_unauthenticated_full_case(case, jurisdiction, client):
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
    case_url = api_reverse("casemetadata-detail", args=[case.id])

    response = client.get(case_url, {"full_case": "true"})
    check_response(response)
    content = response.json()
    assert "casebody" in content
    assert type(content['casebody']['data']) is dict

    jurisdiction.whitelisted = False
    jurisdiction.save()
    case.jurisdiction = jurisdiction
    case.save()

    response = client.get(case_url, {"full_case": "true"})
    check_response(response)
    content = response.json()
    casebody = content['casebody']
    assert 'error_' in casebody['status']
    assert not casebody['data']

    response = client.get(case_url, {"full_case": "true", "format": "xml"})
    check_response(response, content_type="application/xml", content_includes='error_auth_required')

    response = client.get(case_url, {"full_case": "true", "format": "html"})
    check_response(response, content_type="text/html", content_includes='<h1>Error: Not Authenticated')


@pytest.mark.django_db
def test_authenticated_full_case_whitelisted(auth_user, auth_client, case):
    ### whitelisted jurisdiction should not be counted against the user

    case.jurisdiction.whitelisted = True
    case.jurisdiction.save()

    response = auth_client.get(api_reverse("casemetadata-detail", args=[case.id]), {"full_case": "true"})
    check_response(response)
    result = response.json()
    casebody = result['casebody']
    assert casebody['status'] == 'ok'
    assert type(casebody['data']) is dict

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance


@pytest.mark.django_db
def test_authenticated_full_case_blacklisted(auth_user, auth_client, case):
    ### blacklisted jurisdiction cases should be counted against the user

    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()

    response = auth_client.get(api_reverse("casemetadata-detail", args=[case.id]), {"full_case": "true"})
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # make sure the auth_user's case download number has gone down by 1
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 1


@pytest.mark.django_db
def test_unlimited_access(auth_user, auth_client, case):
    ### user with unlimited access should not have blacklisted cases count against them
    auth_user.total_case_allowance = 500
    auth_user.unlimited_access_until = timedelta(hours=24) + timezone.now()
    auth_user.save()
    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()
    case_url = api_reverse("casemetadata-detail", args=[case.id])

    response = auth_client.get(case_url, {"full_case": "true"})
    check_response(response)
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance

    # total_case_allowance shouldn't matter if unlimited access is in effect
    auth_user.total_case_allowance = 0
    auth_user.case_allowance_remaining = 0
    auth_user.save()
    response = auth_client.get(case_url, {"full_case": "true"})
    check_response(response)
    result = response.json()
    casebody = result['casebody']
    assert casebody['status'] == 'ok'
    assert type(casebody['data']) is dict

    # don't allow user to download blacklisted case if unlimited access has expired
    # and they don't have enough case allowance
    auth_user.total_case_allowance = 0
    auth_user.case_allowance_remaining = 0
    auth_user.unlimited_access_until = timezone.now() - timedelta(hours=1)
    auth_user.save()
    response = auth_client.get(case_url, {"full_case": "true"})
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] != 'ok'


@pytest.mark.django_db
def test_authenticated_multiple_full_cases(auth_user, auth_client, three_cases, jurisdiction, django_assert_num_queries):
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
    with django_assert_num_queries(select=3):
        response = auth_client.get(api_reverse("casemetadata-list"), {"full_case": "true"})
    check_response(response)
    # make sure the auth_user's case download number has gone down by 2
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 2


# CITATION REDIRECTS
@pytest.mark.django_db
def test_case_citation_redirect(client, citation):
    """Should allow various forms of citation, should redirect to normalized_cite"""
    url = api_reverse("casemetadata-detail", args=[citation.normalized_cite])

    # should have received a redirect
    response = client.get(url)
    check_response(response, status_code=302)

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
    url = api_reverse("casemetadata-get-cite", args=[citation.cite])
    response = client.get(url, follow=True)

    check_response(response)
    content = response.json()['results']
    case = citation.case
    assert len(content) == 1
    assert content[0]['id'] == case.id

    # citation redirect should work with periods in the url, too
    new_citation = CitationFactory(cite='1 Mass. 1', normalized_cite='1-mass-1', case=citation.case)
    new_citation.save()

    url = api_reverse("casemetadata-get-cite", args=[new_citation.cite])
    response = client.get(url)
    check_response(response, status_code=302)
    response = client.get(url, follow=True)
    check_response(response)
    content = response.json()['results']
    case = citation.case
    assert len(content) == 1
    assert content[0]['id'] == case.id


# FORMATS
def get_casebody_data_with_format(client, case, body_format):
    response = client.get(api_reverse('casemetadata-detail', args=[case.pk]), {"full_case": "true", "body_format": body_format})
    check_response(response)
    content = response.json()
    casebody = content["casebody"]
    assert casebody['status'] == "ok"
    return casebody['data']

@pytest.mark.django_db
def test_body_format_default(auth_client, case):
    data = get_casebody_data_with_format(auth_client, case, "")
    assert type(data["judges"]) is list
    assert type(data["attorneys"]) is list
    assert type(data["parties"]) is list
    opinion = data["opinions"][0]
    assert set(opinion.keys()) == {'type', 'author', 'text'}
    assert opinion["text"]

@pytest.mark.django_db
def test_body_format_xml(auth_client, case):
    data = get_casebody_data_with_format(auth_client, case, "xml")
    assert "<?xml version=" in data

@pytest.mark.django_db
def test_body_format_html(auth_client, case):
    data = get_casebody_data_with_format(auth_client, case, "html")
    assert "</h4>" in data

@pytest.mark.django_db
def test_full_text_search(client, ingest_case_xml):
    # filtering case with full-text search
    case_to_test = CaseXML.objects.get(metadata__case_id="32044057892259_0001").metadata
    wrong_case = CaseXML.objects.get(metadata__duplicative=True).metadata
    response = client.get(api_reverse("casemetadata-list"), {"search": "insurance peoria"})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]
    assert [wrong_case.id] != [result['id'] for result in content['results']]
    response = client.get(api_reverse("casemetadata-list"), {"search": "Punk in Drublic"})
    content = response.json()
    assert content == {'previous': None, 'count': 0, 'results': [], 'next': None}

# FILTERING
@pytest.mark.django_db
def test_filter_case(client, three_cases, court, jurisdiction):
    search_url = api_reverse("casemetadata-list")

    # filtering case by court
    case_to_test = three_cases[2]
    case_to_test.court = court
    case_to_test.save()

    # filtering case by name_abbreviation
    case_to_test = three_cases[0]
    case_to_test.name_abbreviation = "Bill v. Bob"
    case_to_test.save()
    assert case_to_test.name_abbreviation != three_cases[1].name_abbreviation
    response = client.get(search_url, {"name_abbreviation": case_to_test.name_abbreviation})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by name_abbreviation lowercased substring
    assert case_to_test.name_abbreviation != three_cases[1].name_abbreviation
    response = client.get(search_url, {"name_abbreviation": "bill"})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by court substring
    case_to_test = three_cases[2]
    court = case_to_test.court
    response = client.get(search_url, {"court": court.slug})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by reporter
    reporter = case_to_test.reporter
    response = client.get(search_url, {"reporter": reporter.pk})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering by decision_date
    # make sure that we can filter by decision_date's datefield
    # but we get decision_date_original string in response
    case_to_test = three_cases[0]
    case_to_test.decision_date_original = "1988"
    case_to_test.decision_date = parse_decision_date(case_to_test.decision_date_original)
    case_to_test.save()
    response = client.get(search_url, {"decision_date_min": "1987-12-30", "decision_date_max": "1988-01-02"})
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
    response = client.get(search_url, {"jurisdiction": jurisdiction.name}, follow=True)
    content = response.json()
    result = content['results'][0]
    assert case_to_test.jurisdiction.slug == result['jurisdiction']['slug']

    # by docket_number
    case_to_test = three_cases[0]
    case_to_test.docket_number = "NUMBER 13-16-00273-CV"
    case_to_test.save()
    response = client.get(search_url, {"docket_number": "13-16-00273"})
    content = response.json()
    result = content['results'][0]
    assert case_to_test.docket_number== result['docket_number']



@pytest.mark.django_db
def test_filter_court(client, court):
    # filtering court by jurisdiction
    jur_slug = court.jurisdiction.slug
    response = client.get(api_reverse("court-list"), {"jurisdiction_slug": jur_slug})
    check_response(response)
    results = response.json()['results']
    assert court.name_abbreviation == results[0]['name_abbreviation']

    # filtering court by name substring
    court_name_str = court.name.split(' ')[1]
    response = client.get(api_reverse("court-list"), {"name": court_name_str})
    content = response.json()
    for result in content['results']:
        assert court_name_str in result['name']


@pytest.mark.django_db
def test_filter_reporter(client, reporter):
    # filtering reporter by name substring
    reporter_name_str = reporter.full_name.split(' ')[1]
    response = client.get(api_reverse("reporter-list"), {"full_name": reporter_name_str})
    content = response.json()
    for result in content['results']:
        assert reporter_name_str in result['full_name']


# RESPONSE FORMATS
@pytest.mark.django_db
@pytest.mark.parametrize("format, content_type", [
    ('html', 'text/html'),
    ('xml', 'application/xml'),
    ('json', 'application/json'),
])
def test_formats(client, auth_client, case, format, content_type):
    # test format without api_key
    response = client.get(api_reverse("casemetadata-detail", args=[case.id]), {"format": format, "full_case": "true"})
    check_response(response, content_type=content_type)
    response_content = response.content.decode()
    assert 'error' in response_content.lower()

    # test full, authorized case
    response = auth_client.get(api_reverse("casemetadata-detail", args=[case.id]), {"format": format, "full_case": "true"})
    check_response(response, content_type=content_type, content_includes=case.name)


# API SPECIFICATION ENDPOINTS
@pytest.mark.django_db
@pytest.mark.parametrize("url, content_type", [
    (api_reverse("schema-swagger-ui"), 'text/html'),
    (api_reverse("schema-json", args=['.json']), 'application/json'),
    (api_reverse("schema-json", args=['.yaml']), 'application/yaml'),
])
def test_swagger(client, url, content_type):
    response = client.get(url)
    check_response(response, content_type=content_type)


@pytest.mark.django_db
def test_redoc(client):
    response = client.get(api_reverse("schema-redoc"))
    check_response(response, content_type="text/html")
