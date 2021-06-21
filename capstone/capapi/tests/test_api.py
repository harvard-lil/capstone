from flaky import flaky

from capapi import api_reverse
from capdb.tasks import update_elasticsearch_from_queue
from test_data.test_fixtures.factories import *
from capapi.tests.helpers import check_response
from user_data.models import UserHistory


@pytest.mark.django_db(databases=['capdb'])
def test_flow(client, unrestricted_case, elasticsearch):
    """user should be able to click through to get to different tables"""
    # start with case
    response = client.get(api_reverse("cases-detail", args=[unrestricted_case.id]))
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
    assert content.get("name") == unrestricted_case.jurisdiction.name


# RESOURCE ENDPOINTS
@pytest.mark.django_db(databases=['capdb'])
@pytest.mark.parametrize("fixture_name, detail_attr, comparison_attr", [
    ("jurisdiction", "slug", "name_long"),
    ("court", "slug", "name"),
    ("reporter", "pk", "full_name"),
    ("volume_metadata", "pk", "title"),
    ("case_export", "pk", "file_name"),
])
def test_model_endpoint(request, client, fixture_name, detail_attr, comparison_attr):
    """ Generic test to kick the tires on -list and -detail for model endpoints. """
    instance = request.getfixturevalue(fixture_name)
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

@pytest.mark.django_db(databases=['capdb'])
def test_cases_endpoint(client, unrestricted_case, elasticsearch):
    # test list endpoint
    case_list_url = api_reverse("cases-list")
    response = client.get(case_list_url)
    assert response.json()['count'] == 1

    # test detail endpoint
    response = client.get(api_reverse("cases-detail", args=[unrestricted_case.id]))
    check_response(response)
    results = response.json()
    assert results['name'] == unrestricted_case.name

# REQUEST AUTHORIZATION
@pytest.mark.django_db(databases=['default', 'capdb'])
def test_unauthorized_request(cap_user, client, restricted_case, elasticsearch):
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance
    client.credentials(HTTP_AUTHORIZATION='Token fake')
    response = client.get(api_reverse("cases-detail", args=[restricted_case.id]), {"full_case": "true"})
    check_response(response, status_code=401)

    cap_user.refresh_from_db()
    assert cap_user.case_allowance_remaining == cap_user.total_case_allowance

@pytest.mark.django_db(databases=['capdb'])
def test_unauthenticated_full_case(unrestricted_case, restricted_case, client, elasticsearch):
    """
    we should allow users to get full case without authentication
    if case is whitelisted
    we should allow users to see why they couldn't get full case
    if case is blacklisted
    """
    case_url = api_reverse("cases-detail", args=[unrestricted_case.id])

    response = client.get(case_url, {"full_case": "true"})
    check_response(response)
    content = response.json()
    assert "casebody" in content
    assert type(content['casebody']['data']) is dict

    case_url = api_reverse("cases-detail", args=[restricted_case.id])
    response = client.get(case_url, {"full_case": "true"})
    check_response(response)
    content = response.json()
    casebody = content['casebody']
    assert 'error_' in casebody['status']
    assert not casebody['data']


@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_authenticated_full_case_whitelisted(auth_user, auth_client, unrestricted_case, elasticsearch):
    ### whitelisted jurisdiction should not be counted against the user

    response = auth_client.get(api_reverse("cases-detail", args=[unrestricted_case.id]), {"full_case": "true"})
    check_response(response)
    result = response.json()
    casebody = result['casebody']
    assert casebody['status'] == 'ok'
    assert type(casebody['data']) is dict

    # make sure the user's case download number has remained the same
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance


@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_authenticated_full_case_blacklisted(auth_user, auth_client, restricted_case, elasticsearch):
    ### blacklisted jurisdiction cases should be counted against the user

    response = auth_client.get(api_reverse("cases-detail", args=[restricted_case.id]), {"full_case": "true"})
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # make sure the auth_user's case download number has gone down by 1
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 1


def test_case_detail_pdf(transactional_db, client, auth_client, restricted_case, unrestricted_case, elasticsearch):
    """ Test ?format=pdf on case detail API. """
    content_type = 'application/pdf'
    case_text = "REMEMBERED"
    CaseMetadata.objects.update(first_page_order=1, last_page_order=3)

    # unauthorized request can't fetch restricted PDF
    response = client.get(api_reverse("cases-detail", args=[restricted_case.id]), {"full_case": "true", "format": "pdf"})
    check_response(response, status_code=400)

    # authorized request can fetch restricted PDF
    response = auth_client.get(api_reverse("cases-detail", args=[restricted_case.id]), {"full_case": "true", "format": "pdf"})
    check_response(response, content_includes=case_text, content_type=content_type)

    # both can fetch unrestricted PDF
    response = client.get(api_reverse("cases-detail", args=[unrestricted_case.id]), {"full_case": "true", "format": "pdf"})
    check_response(response, content_includes=case_text, content_type=content_type)
    response = auth_client.get(api_reverse("cases-detail", args=[unrestricted_case.id]), {"full_case": "true", "format": "pdf"})
    check_response(response, content_includes=case_text, content_type=content_type)

    # ?format=pdf only works on detail page
    response = auth_client.get(api_reverse("cases-list", args=[unrestricted_case.id]), {"full_case": "true", "format": "pdf"})
    check_response(response, status_code=404)


def test_csv(transactional_db, client, auth_client, restricted_case, unrestricted_case, elasticsearch):
    """ Test ?format=csv on case detail and list API. """
    content_type = 'text/csv'
    case_text = "Opinion text"

    # unauthorized request can't fetch restricted TSV
    response = client.get(api_reverse("cases-detail", args=[restricted_case.id]),
                          {"full_case": "true", "format": "csv"})
    check_response(response, content_excludes=case_text, content_type=content_type)

    # authorized request can fetch restricted TSV
    response = auth_client.get(api_reverse("cases-detail", args=[restricted_case.id]), {"full_case": "true", "format": "csv"})
    check_response(response, content_includes=case_text, content_type=content_type)

    # both can fetch unrestricted TSV
    response = client.get(api_reverse("cases-detail", args=[unrestricted_case.id]),
                          {"full_case": "true", "format": "csv"})
    check_response(response, content_includes=case_text, content_type=content_type)
    response = auth_client.get(api_reverse("cases-detail", args=[unrestricted_case.id]),
                               {"full_case": "true", "format": "csv"})
    check_response(response, content_includes=case_text, content_type=content_type)

    # ?format=csv works on list page
    response = auth_client.get(api_reverse("cases-list"), {"full_case": "true", "format": "csv", "page_size": "100"})
    # each row separated by '\n'
    decoded_response = ""
    for res in response.streaming_content:
        decoded_response += res.decode()

    # -1 for headers, -1 for last newline '\n'
    response_count = len(decoded_response.split('\n')) - 2
    assert response_count == CaseMetadata.objects.count()
    assert case_text in decoded_response
    check_response(response, content_type=content_type)


@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_track_history(auth_user, auth_client, restricted_case, elasticsearch):
    # initial fetch
    url = api_reverse("cases-detail", args=[restricted_case.id])
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
    assert [(h.case_id, h.user_id) for h in UserHistory.objects.all()] == [(restricted_case.id, auth_user.id)]

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


@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_unlimited_access(auth_user, auth_client, restricted_case, elasticsearch):
    ### user with unlimited access should not have blacklisted cases count against them
    auth_user.total_case_allowance = settings.API_CASE_DAILY_ALLOWANCE
    auth_user.unlimited_access = True
    auth_user.unlimited_access_until = timedelta(hours=24) + timezone.now()
    auth_user.save()
    case_url = api_reverse("cases-detail", args=[restricted_case.id])

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


@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
@pytest.mark.parametrize("client_fixture_name", ["auth_client", "token_auth_client"])
def test_harvard_access(request, restricted_case, client_fixture_name, elasticsearch):
    ### user with harvard access can download from harvard IPs, even without case allowance
    client = request.getfixturevalue(client_fixture_name)
    user = client.auth_user
    user.harvard_access = True
    user.case_allowance_remaining = 1
    user.save()
    case_url = api_reverse("cases-detail", args=[restricted_case.id])

    # request works when IP address provided
    response = client.get(case_url, {"full_case": "true"}, HTTP_CF_CONNECTING_IP='128.103.1.1')
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # no case allowance used
    user.refresh_from_db()
    assert user.case_allowance_remaining == 1

    # request succeeds when IP address is wrong, using case allowance
    response = client.get(case_url, {"full_case": "true"}, HTTP_CF_CONNECTING_IP='1.1.1.1')
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # case allowance used
    user.refresh_from_db()
    assert user.case_allowance_remaining == 0

    # request fails when case allowance exhausted
    response = client.get(case_url, {"full_case": "true"}, HTTP_CF_CONNECTING_IP='1.1.1.1')
    check_response(response)
    result = response.json()
    assert result['casebody']['status'] != 'ok'


@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_authenticated_multiple_full_cases(auth_user, auth_client, case_factory, elasticsearch):
    ### mixed requests should be counted only for blacklisted cases

    [case_factory(jurisdiction__whitelisted=False) for i in range(2)]
    [case_factory(jurisdiction__whitelisted=True) for i in range(1)]

    response = auth_client.get(api_reverse("cases-list"), {"full_case": "true"})
    check_response(response)
    assert response.json()['count'] == 3

    # make sure the auth_user's case download number has gone down by 2
    auth_user.refresh_from_db()
    assert auth_user.case_allowance_remaining == auth_user.total_case_allowance - 2


# CITATION REDIRECTS
@pytest.mark.django_db(databases=['capdb'])
def test_case_citation_redirect(client, case_factory, elasticsearch):
    """Should allow various forms of citation, should redirect to normalized_cite"""
    case = case_factory(citations__cite='123 Mass. App. 456')
    citation = case.citations.first()
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


# FORMATS
def get_casebody_data_with_format(client, case_id, body_format):
    response = client.get(api_reverse('cases-detail', args=[case_id]), {"full_case": "true", "body_format": body_format})
    check_response(response)
    content = response.json()
    casebody = content["casebody"]
    assert casebody['status'] == "ok"
    return casebody['data']

@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_body_format_default(auth_client, restricted_case, elasticsearch):
    data = get_casebody_data_with_format(auth_client, restricted_case.id, "")
    assert type(data["judges"]) is list
    assert type(data["attorneys"]) is list
    assert type(data["parties"]) is list
    opinion = data["opinions"][0]
    assert set(opinion.keys()) == {'type', 'author', 'text'}
    assert opinion["text"]

@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_body_format_unrecognized(auth_client, restricted_case, elasticsearch):
    data = get_casebody_data_with_format(auth_client, restricted_case.id, "uh_oh_not_a_real_format")
    assert type(data["judges"]) is list
    assert type(data["attorneys"]) is list
    assert type(data["parties"]) is list
    opinion = data["opinions"][0]
    assert set(opinion.keys()) == {'type', 'author', 'text'}
    assert opinion["text"]


@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_body_format_xml(auth_client, restricted_case, elasticsearch):
    data = get_casebody_data_with_format(auth_client, restricted_case.id, "xml")
    assert "<?xml version=" in data

@pytest.mark.django_db(databases=['default', 'capdb', 'user_data'])
def test_body_format_html(auth_client, restricted_case, elasticsearch):
    data = get_casebody_data_with_format(auth_client, restricted_case.id, "html")
    assert restricted_case.body_cache.html in data

@pytest.mark.django_db(databases=['capdb'])
def test_full_text_search(client, case_factory, elasticsearch):
    case1 = case_factory(name_abbreviation="111 222 333 555666")
    case2 = case_factory(name_abbreviation="111 stop 222 444 555777")
    case_factory(name_abbreviation="nothing matching")

    # AND queries
    response = client.get(api_reverse("cases-list"), {"search": "111 222"})
    content = response.json()
    assert {case1.id, case2.id} == set(result['id'] for result in content['results'])

    # OR queries
    response = client.get(api_reverse("cases-list"), {"search": "333 | 444"})
    content = response.json()
    assert {case1.id, case2.id} == set(result['id'] for result in content['results'])

    # phrase search
    response = client.get(api_reverse("cases-list"), {"search": '"111 222"'})
    content = response.json()
    assert {case1.id} == set(result['id'] for result in content['results'])

    # prefix search
    response = client.get(api_reverse("cases-list"), {"search": '555*'})
    content = response.json()
    assert {case1.id, case2.id} == set(result['id'] for result in content['results'])

    # empty search
    response = client.get(api_reverse("cases-list"), {"search": "Some other search that doesn't work"})
    content = response.json()
    assert content == { "count":0, "next": None, "previous": None, "results": []}


# FILTERING
@pytest.mark.django_db(databases=['capdb'])
def test_filter_case(client, case_factory, elasticsearch):
    cases = [case_factory() for _ in range(3)]
    search_url = api_reverse("cases-list")

    # filtering case by name_abbreviation
    case_to_test = cases[0]
    response = client.get(search_url, {"name_abbreviation": case_to_test.name_abbreviation})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by name_abbreviation lowercased substring
    response = client.get(search_url, {"name_abbreviation": case_to_test.name_abbreviation.lower()})
    content = response.json()
    assert [case_to_test.id] == [result['id'] for result in content['results']]

    # filtering case by court slug
    case_to_test = cases[2]
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
    case_to_test = cases[0]
    decision_date = case_to_test.decision_date_original
    response = client.get(search_url, {"decision_date_min": decision_date, "decision_date_max": decision_date})
    content = response.json()
    result = content['results'][0]
    assert case_to_test.id == result['id']

    # by jurisdiction
    response = client.get(search_url, {"jurisdiction": case_to_test.jurisdiction.slug}, follow=True)
    content = response.json()
    assert content['count'] == 1
    jurisdictions = set([ result['jurisdiction']['slug'] for result in content['results'] ])
    assert jurisdictions == {case_to_test.jurisdiction.slug}

    # by docket_number
    case_to_test = cases[0]
    response = client.get(search_url, {"docket_number": case_to_test.docket_number})
    content = response.json()
    result = content['results'][0]
    assert case_to_test.docket_number == result['docket_number']


@pytest.mark.django_db(databases=['capdb'])
def test_filter_case_cite_by(client, extracted_citation_factory, case_factory, elasticsearch):
    search_url = api_reverse("cases-list")
    cases = [case_factory() for _ in range(4)]
    cite_text = '1 Mass. 1'
    case_cited = case_factory(citations__cite=cite_text)
    for c in cases[:-1]:
        extracted_citation_factory(
            cited_by=c,
            cite=cite_text,
            normalized_cite=normalize_cite(cite_text),
            target_case=case_cited,
            target_cases=[case_cited.id])
    update_elasticsearch_from_queue()

    # get cases by cites_to=citation
    content = client.get(search_url, {"cites_to": cite_text}).json()
    assert set(case['id'] for case in content['results']) == set(c.id for c in cases[:-1])

    # get cases by cites_to=id
    content = client.get(search_url, {"cites_to": case_cited.id}).json()
    assert set(case['id'] for case in content['results']) == set(c.id for c in cases[:-1])


@pytest.mark.django_db(databases=['capdb'])
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


@pytest.mark.django_db(databases=['capdb'])
def test_filter_reporter(client, reporter):
    # filtering reporter by name substring
    reporter_name_str = reporter.full_name.split(' ')[1]
    response = client.get(api_reverse("reporter-list"), {"full_name": reporter_name_str})
    content = response.json()
    for result in content['results']:
        assert reporter_name_str in result['full_name']


# NGRAMS

@flaky(max_runs=10)  # ngrammed_cases call to ngram_jurisdictions doesn't reliably work because it uses multiprocessing within pytest environment
@pytest.mark.django_db(databases=['capdb'])
def test_ngrams_api(client, request):
    ngrammed_cases = request.getfixturevalue('ngrammed_cases')  # load fixture inside test so flaky() can catch errors

    # check result counts when not filtering by jurisdiction
    json = client.get(api_reverse('ngrams-list'), {'q': 'one two'}).json()
    assert json['results'] == {
        'one two': {
            'total': [{'year': '2000', 'count': [2, 9], 'doc_count': [2, 3]}]}}

    # check result counts when filtering by jurisdiction
    json = client.get(api_reverse('ngrams-list'), {'q': 'one two', 'jurisdiction': ngrammed_cases[1].jurisdiction.slug}).json()
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


# API SPECIFICATION ENDPOINTS
@pytest.mark.django_db(databases=['capdb'])
@pytest.mark.parametrize("url, content_type", [
    (api_reverse("schema-swagger-ui"), 'text/html'),
    (api_reverse("schema-json", args=['.json']), 'application/json'),
    (api_reverse("schema-json", args=['.yaml']), 'application/yaml'),
])
def test_swagger(client, url, content_type):
    response = client.get(url)
    check_response(response, content_type=content_type)


def test_redoc(client):
    response = client.get(api_reverse("schema-redoc"))
    check_response(response, content_type="text/html")


# PAGINATION
@pytest.mark.django_db(databases=['capdb'])
def test_pagination(client, case_factory, elasticsearch):
    cases = [case_factory() for _ in range(3)]

    orderings = ['relevance', 'decision_date', '-decision_date']
    ids = []
    for ordering in orderings:
        content = client.get(api_reverse("cases-list"), {"page_size": 1, "ordering": ordering}).json()
        assert len(content['results']) == 1
        ids.append(content['results'][0]['id'])

        content = client.get(content['next']).json()
        assert len(content['results']) == 1
        ids.append(content['results'][0]['id'])

        content = client.get(content['next']).json()
        assert len(content['results']) == 1
        ids.append(content['results'][0]['id'])
        assert content['next'] is None

        content = client.get(content['previous']).json()
        assert len(content['results']) == 1
        ids.append(content['results'][0]['id'])

        content = client.get(content['previous']).json()
        assert len(content['results']) == 1
        ids.append(content['results'][0]['id'])
        assert content['previous'] is None


    assert set(ids) == set(case.id for case in cases)
