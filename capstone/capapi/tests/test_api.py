import pytest
from flaky import flaky

from capapi import api_reverse
from test_data.test_fixtures.factories import *
from capapi.tests.helpers import check_response

from capdb.models import Citation, Jurisdiction
from user_data.models import UserHistory


@pytest.mark.django_db
def test_flow(client, whitelisted_case_document):
    """user should be able to click through to get to different tables"""
    # start with case
    response = client.get(api_reverse("cases-detail", args=[whitelisted_case_document.id]))
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
    assert content.get("name") == whitelisted_case_document.jurisdiction.name


@pytest.mark.django_db
def test_jurisdiction_redirect(client, non_whitelisted_case_document):

    jurisdiction = Jurisdiction.objects.get(slug=non_whitelisted_case_document.jurisdiction.slug)

    response = client.get(api_reverse("cases-list"), {"jurisdiction": jurisdiction.name}, follow=True)
    query_string = response.request.get('QUERY_STRING')
    query, jurisdiction_name = query_string.split('=')
    assert jurisdiction_name == jurisdiction.name


# RESOURCE ENDPOINTS
@pytest.mark.django_db
@pytest.mark.parametrize("fixture_name, detail_attr, comparison_attr", [
    ("jurisdiction", "slug", "name_long"),
    ("court", "slug", "name"),
    ("reporter", "pk", "full_name"),
    ("volume_metadata", "pk", "title"),
    ("case_export", "pk", "file_name"),
    ("citation", "pk", "cite"),
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
def test_cases_endpoint(client, whitelisted_case_document):
    # test list endpoint
    case_list_url = api_reverse("cases-list")
    response = client.get(case_list_url)
    assert response.json()['count'] == 3

    # test detail endpoint
    response = client.get(api_reverse("cases-detail", args=[whitelisted_case_document.id]))
    check_response(response)
    results = response.json()
    assert results['name'] == whitelisted_case_document.name

# REQUEST AUTHORIZATION
@pytest.mark.django_db
def test_unauthorized_request(cap_user, client, non_whitelisted_case_document):
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance
    client.credentials(HTTP_AUTHORIZATION='Token fake')
    response = client.get(api_reverse("cases-detail", args=[non_whitelisted_case_document.id]), {"full_case": "true"})
    check_response(response, status_code=401)

    cap_user.refresh_from_db()
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance

@pytest.mark.django_db
def test_unauthenticated_full_case(whitelisted_case_document, non_whitelisted_case_document, client):
    """
    we should allow users to get full case without authentication
    if case is whitelisted
    we should allow users to see why they couldn't get full case
    if case is blacklisted
    """
    case_url = api_reverse("cases-detail", args=[whitelisted_case_document.id])

    response = client.get(case_url, {"full_case": "true"})
    check_response(response)
    content = response.json()
    assert "casebody" in content
    assert type(content['casebody']['data']) is dict

    case_url = api_reverse("cases-detail", args=[non_whitelisted_case_document.id])
    response = client.get(case_url, {"full_case": "true"})
    check_response(response)
    content = response.json()
    casebody = content['casebody']
    assert 'error_' in casebody['status']
    assert not casebody['data']

    response = client.get(case_url, {"full_case": "true", "format": "xml"})
    check_response(response, content_type="application/xml", content_includes='error_auth_required')

    response = client.get(case_url, {"full_case": "true", "format": "html"})
    check_response(response, content_type="text/html", content_includes='You must be signed in to see the full case')


@pytest.mark.django_db
def test_authenticated_full_case_whitelisted(auth_user, auth_client, whitelisted_case_document):
    ### whitelisted jurisdiction should not be counted against the user

    response = auth_client.get(api_reverse("cases-detail", args=[whitelisted_case_document.id]), {"full_case": "true"})
    check_response(response)
    result = response.json()
    casebody = result['casebody']
    assert casebody['status'] == 'ok'
    assert type(casebody['data']) is dict

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance


@pytest.mark.django_db
def test_authenticated_full_case_blacklisted(auth_user, auth_client, non_whitelisted_case_document):
    ### blacklisted jurisdiction cases should be counted against the user

    response = auth_client.get(api_reverse("cases-detail", args=[non_whitelisted_case_document.id]), {"full_case": "true"})
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # make sure the auth_user's case download number has gone down by 1
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 1


@pytest.mark.django_db
def test_track_history(auth_user, auth_client, non_whitelisted_case_document, auth_user_factory):
    # initial fetch
    url = api_reverse("cases-detail", args=[non_whitelisted_case_document.id])
    kwargs = {"full_case": "true"}
    response = auth_client.get(url, kwargs)
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # make sure the auth_user's case download number has gone down by 1
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 1

    # make sure no history is tracked
    assert UserHistory.objects.count() == 0

    # fetch with history tracking
    auth_user.track_history = True
    auth_user.save()
    response = auth_client.get(url, kwargs)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # make sure the auth_user's case download number has gone down by 1
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 2

    # history object now exists
    assert [(h.case_id, h.user_id) for h in UserHistory.objects.all()] == [(non_whitelisted_case_document.id, auth_user.id)]

    # fetch again with history tracking
    auth_user.track_history = True
    auth_user.save()
    response = auth_client.get(url, kwargs)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # download number has not gone down after second fetch with history tracking
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 2

    # user can still fetch this case even when quota exhausted
    auth_user.case_allowance_remaining = 0
    auth_user.save()
    response = auth_client.get(url, kwargs)
    result = response.json()
    assert result['casebody']['status'] == 'ok'
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == 0


@pytest.mark.django_db
def test_unlimited_access(auth_user, auth_client, non_whitelisted_case_document):
    ### user with unlimited access should not have blacklisted cases count against them
    auth_user.total_case_allowance = settings.API_CASE_DAILY_ALLOWANCE
    auth_user.unlimited_access = True
    auth_user.unlimited_access_until = timedelta(hours=24) + timezone.now()
    auth_user.save()
    case_url = api_reverse("cases-detail", args=[non_whitelisted_case_document.id])

    response = auth_client.get(case_url, {"full_case": "true"})
    check_response(response)
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance

    # total_case_allowance shouldn't matter if unlimited access is in effect
    auth_user.total_case_allowance = 0
    auth_user.case_allowance_remaining = 0
    auth_user.unlimited_access_until = None
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
@pytest.mark.parametrize("client_fixture_name", ["auth_client", "token_auth_client"])
def test_harvard_access(request, non_whitelisted_case_document, client_fixture_name):
    ### user with harvard access can download from harvard IPs, even without case allowance
    client = request.getfuncargvalue(client_fixture_name)
    user = client.auth_user
    user.harvard_access = True
    user.case_allowance_remaining = 1
    user.save()
    case_url = api_reverse("cases-detail", args=[non_whitelisted_case_document.id])

    # request works when IP address provided
    response = client.get(case_url, {"full_case": "true"}, HTTP_X_FORWARDED_FOR='128.103.1.1')
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # no case allowance used
    user.refresh_from_db()
    assert user.case_allowance_remaining == 1

    # request succeeds when IP address is wrong, using case allowance
    response = client.get(case_url, {"full_case": "true"}, HTTP_X_FORWARDED_FOR='1.1.1.1')
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # case allowance used
    user.refresh_from_db()
    assert user.case_allowance_remaining == 0

    # request fails when case allowance exhausted
    response = client.get(case_url, {"full_case": "true"}, HTTP_X_FORWARDED_FOR='1.1.1.1')
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] != 'ok'


@pytest.mark.django_db
def test_authenticated_multiple_full_cases(auth_user, auth_client, ingest_elasticsearch):
    ### mixed requests should be counted only for blacklisted cases

    response = auth_client.get(api_reverse("cases-list"), {"full_case": "true"})
    check_response(response)
    assert response.json()['count'] == 3

    # make sure the auth_user's case download number has gone down by 2
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 1


# CITATION REDIRECTS
@pytest.mark.django_db
def test_case_citation_redirect(client, in_re_the_marriage_of_lyle, taylor_v_sprinkle):
    """Should allow various forms of citation, should redirect to normalized_cite"""
    citation = Citation.objects.get(case_id=in_re_the_marriage_of_lyle['id'])
    url = api_reverse("cases-detail", args=[citation.normalized_cite])

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
    url = api_reverse("case-get-cite", args=[citation.cite])
    response = client.get(url, follow=True)

    check_response(response)
    content = response.json()['results']
    case = citation.case
    assert len(content) == 1
    assert content[0]['id'] == case.id

    # citation redirect should work with periods in the url, too
    citation = Citation.objects.get(case_id=taylor_v_sprinkle['id'])
    url = api_reverse("case-get-cite", args=[citation.cite])
    response = client.get(url)
    check_response(response, status_code=302)
    response = client.get(url, follow=True)
    check_response(response)
    content = response.json()['results']
    case = citation.case
    assert len(content) == 1
    assert content[0]['id'] == case.id


# FORMATS
def get_casebody_data_with_format(client, case_id, body_format):
    response = client.get(api_reverse('cases-detail', args=[case_id]), {"full_case": "true", "body_format": body_format})
    check_response(response)
    content = response.json()
    casebody = content["casebody"]
    assert casebody['status'] == "ok"
    return casebody['data']

@pytest.mark.django_db
def test_body_format_default(auth_client, non_whitelisted_case_document):
    data = get_casebody_data_with_format(auth_client, non_whitelisted_case_document.id, "")
    assert type(data["judges"]) is list
    assert type(data["attorneys"]) is list
    assert type(data["parties"]) is list
    opinion = data["opinions"][0]
    assert set(opinion.keys()) == {'type', 'author', 'text'}
    assert opinion["text"]

@pytest.mark.django_db
def test_body_format_xml(auth_client, non_whitelisted_case_document):
    data = get_casebody_data_with_format(auth_client, non_whitelisted_case_document.id, "xml")
    assert "<?xml version=" in data

@pytest.mark.django_db
def test_body_format_html(auth_client, non_whitelisted_case_document):
    data = get_casebody_data_with_format(auth_client, non_whitelisted_case_document.id, "html")
    assert "</h4>" in data

@pytest.mark.django_db
def test_full_text_search(client, home_insurance_co_of_new_york_v_kirk):
    # filtering case with full-text search
    response = client.get(api_reverse("cases-list"), {"search": "Home Insurance"})
    content = response.json()
    assert [home_insurance_co_of_new_york_v_kirk['id']] == [result['id'] for result in content['results']]
    response = client.get(api_reverse("cases-list"), {"search": "Some other search that doesn't work"})
    content = response.json()
    assert content == { "count":0, "next": None, "previous": None, "facets": {}, "results": []}


# FILTERING
@pytest.mark.django_db
def test_filter_case(client, three_case_documents):
    search_url = api_reverse("cases-list")


    # filtering case by court
    response = client.get(search_url, {"court": 'ill'}, follow=True)
    content = response.json()
    assert content['count'] == 1
    results = set([ result['court']['slug'] for result in content['results'] ])
    assert results == {'ill'}


    # filtering case by name_abbreviation
    case_to_test = three_case_documents[0]
    response = client.get(search_url, {"name_abbreviation": case_to_test.name_abbreviation})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]


    # filtering case by name_abbreviation lowercased substring
    response = client.get(search_url, {"name_abbreviation": case_to_test.name_abbreviation.lower()})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by court substring
    case_to_test = three_case_documents[2]
    response = client.get(search_url, {"court": case_to_test.court.slug})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by court id
    response = client.get(search_url, {"court_id": case_to_test.court.id})
    content = response.json()
    assert len(content['results']) == 1
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by reporter
    reporter = case_to_test.reporter.id
    response = client.get(search_url, {"reporter": reporter})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering by decision_date
    # make sure that we can filter by decision_date's datefield
    # but we get decision_date_original string in response
    case_to_test = three_case_documents[0]
    response = client.get(search_url, {"decision_date_min": "2017-07-11", "decision_date_max": "2017-07-11"})
    content = response.json()
    result = content['results'][0]
    assert case_to_test.id == result['id']

    # by jurisdiction
    response = client.get(search_url, {"jurisdiction": 'ill'}, follow=True)
    content = response.json()
    assert content['count'] == 2
    jurisdictions = set([ result['jurisdiction']['slug'] for result in content['results'] ])
    assert jurisdictions == {'ill'}

    # by docket_number
    case_to_test = three_case_documents[0]
    response = client.get(search_url, {"docket_number": case_to_test.docket_number})
    content = response.json()
    result = content['results'][0]
    assert case_to_test.docket_number == result['docket_number']



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


# NGRAMS

@flaky(max_runs=10)  # ngrammed_cases call to ngram_jurisdictions doesn't reliably work because it uses multiprocessing within pytest environment
@pytest.mark.django_db
def test_ngrams_api(client, ngrammed_cases):

    # check result counts when not filtering by jurisdiction
    json = client.get(api_reverse('ngrams-list'), {'q': 'one two'}).json()
    assert json['results'] == {
        'one two': {
            'total': [{'year': '2000', 'count': [2, 9], 'doc_count': [2, 3]}]}}

    # check result counts when filtering by jurisdiction
    json = client.get(api_reverse('ngrams-list'), {'q': 'one two', 'jurisdiction': ngrammed_cases[1].jurisdiction_slug}).json()
    assert json['results'] == {
        'one two': {
            'jur1': [{'year': '2000', 'count': [1, 6], 'doc_count': [1, 2]}]}}

    # check wildcard match
    json = client.get(api_reverse('ngrams-list'), {'q': 'three *'}).json()
    assert json['results'] == {
        'three four': {
            'total': [{'year': '2000', 'count': [1, 9], 'doc_count': [1, 3]}]},
        "three don't": {
            'total': [{'year': '2000', 'count': [2, 9], 'doc_count': [2, 3]}]}}


# RESPONSE FORMATS
@pytest.mark.django_db
@pytest.mark.parametrize("format, content_type", [
    ('html', 'text/html'),
    ('xml', 'application/xml'),
    ('json', 'application/json'),
])
def test_formats(client, auth_client, whitelisted_case_document, format, content_type):
    # test format without api_key
    response = client.get(api_reverse("cases-detail", args=[whitelisted_case_document.id]), {"format": format, "full_case": "true"})
    check_response(response, content_type=content_type)
    response_content = response.content.decode()
    assert 'error' in response_content.lower()

    # test full, authorized case
    response = auth_client.get(api_reverse("cases-detail", args=[whitelisted_case_document.id]), {"format": format, "full_case": "true"})
    check_response(response, content_type=content_type, content_includes=whitelisted_case_document.name)


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


# PAGINATION
@pytest.mark.django_db
def test_pagination(client, three_case_documents):
    ids = []

    response = client.get(api_reverse("cases-list"), {"page_size": 1})
    content = response.json()
    assert len(content['results']) == 1
    ids.append(content['results'][0]['id'])

    response = client.get(content['next'])
    content = response.json()
    assert len(content['results']) == 1
    ids.append(content['results'][0]['id'])

    response = client.get(content['next'])
    content = response.json()
    assert len(content['results']) == 1
    ids.append(content['results'][0]['id'])
    assert content['next'] is None

    assert set(ids) == set(case.id for case in three_case_documents)
