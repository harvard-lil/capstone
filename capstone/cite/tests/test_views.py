import re
import json
import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils.text import slugify
from capapi.tests.helpers import check_response, is_cached
from capweb.helpers import reverse
from capweb import helpers
from retry import retry


from scripts.helpers import parse_xml


@pytest.mark.django_db
def test_home(client, django_assert_num_queries, ingest_metadata):
    """ Test / """
    with django_assert_num_queries(select=2):
        response = client.get(reverse('cite_home', host='cite'))
    check_response(response, content_includes="Alabama Appellate Courts Reports")


@pytest.mark.django_db
def test_series(client, django_assert_num_queries, volume_factory):
    """ Test /series/ """

    # make sure we correctly handle multiple reporters with same slug
    volume_1, volume_2 = [volume_factory() for _ in range(2)]
    volume_2.reporter.short_name_slug = volume_1.reporter.short_name_slug
    volume_2.reporter.save()

    with django_assert_num_queries(select=2):
        response = client.get(reverse('series', args=[volume_1.reporter.short_name_slug], host='cite'))
    check_response(response)
    content = response.content.decode()
    for vol in (volume_1, volume_2):
        assert vol.volume_number in content
        assert vol.reporter.full_name in content

    # make sure we redirect if series is not slugified
    series_slug = volume_1.reporter.short_name_slug.replace('-', '. ').upper()
    response = client.get(reverse('series', args=[series_slug], host='cite'))
    check_response(response, status_code=302)
    with django_assert_num_queries(select=2):
        response = client.get(reverse('series', args=[series_slug], host='cite'), follow=True)
    check_response(response, status_code=200)


@pytest.mark.django_db
def test_volume(client, django_assert_num_queries, case_factory):
    """ Test /series/volume/ """

    # make sure we correctly handle multiple reporters with same slug
    case_1, case_2, case_3 = [case_factory() for _ in range(3)]
    for case in [case_2, case_3]:
        case.reporter.short_name_slug = case_1.reporter.short_name_slug
        case.reporter.save()
        case.volume.volume_number = case_1.volume.volume_number
        case.volume.save()

    # make sure we exclude dupes
    case_3.duplicative = True
    case_3.save()

    with django_assert_num_queries(select=3):
        response = client.get(
            reverse('volume', args=[case_1.reporter.short_name_slug, case_1.volume.volume_number], host='cite'))
    check_response(response)
    content = response.content.decode()
    for case in (case_1, case_2):
        assert case.volume.volume_number in content
        assert case.reporter.full_name in content
        assert case.citations.first().cite in content

    assert case_3.citations.first().cite not in content

    # make sure we redirect if reporter name / series is not slugified
    series_slug = case_1.reporter.short_name_slug.replace('-', '. ').upper()
    response = client.get(reverse('volume', args=[series_slug, case_1.volume.volume_number], host='cite'))
    check_response(response, status_code=302)
    with django_assert_num_queries(select=3):
        response = client.get(reverse('volume', args=[series_slug, case_1.volume.volume_number], host='cite'), follow=True)
    check_response(response, status_code=200)


@pytest.mark.django_db
def test_case_not_found(client, ingest_elasticsearch, django_assert_num_queries):
    """ Test /series/volume/case/ not found """
    with django_assert_num_queries(select=1):
        response = client.get(reverse('citation', args=['fake', '123', '456'], host='cite'))
    check_response(response, content_includes='Citation "123 Fake 456" was not found')


@pytest.mark.django_db
def test_cases_multiple(client, django_assert_num_queries, three_case_documents):
    """ Test /series/volume/case/ with multiple matching cases """
    first_case = three_case_documents[0]
    cite = {'type': 'official', 'cite': '23 Ill. App. 19', 'normalized_cite': '23illapp19'}
    for i, case in enumerate(three_case_documents):
        case.citations = [cite]
        case.save()
    cite_parts = re.match(r'(\S+)\s+(.*?)\s+(\S+)$', cite['cite']).groups()

    @retry(tries=10, delay=1)
    def multiple_results(client, cite_parts, three_case_documents):
        response = client.get(
            reverse('citation', args=[slugify(cite_parts[1]), cite_parts[0], cite_parts[2]], host='cite'), follow=True)

        check_response(response, content_includes='Multiple cases match')
        content = response.content.decode()
        for case in three_case_documents:
            assert case.name_abbreviation in content

    multiple_results(client, cite_parts, three_case_documents)

    # load one of the results
    first_case.jurisdiction.whitelisted = True
    first_case.save()

    @retry(tries=10, delay=1)
    def one_of_the_results(client, cite_parts, first_case):
        response = client.get(
            reverse('citation', args=[slugify(cite_parts[1]), cite_parts[0], cite_parts[2], first_case.id], host='cite'))
        check_response(response)

    one_of_the_results(client, cite_parts, first_case)



@retry(tries=10, delay=1)
def retrieve_and_check_response_content(client, url, content_includes, follow=False):
    # this should be used right after an elasticsearch save, so it will retry if
    # what we're looking for isn't immediately available

    response = client.get(url, follow=follow)
    check_response(response, content_includes=content_includes)

@pytest.mark.django_db
def test_single_case(client, auth_client, case_document):
    """ Test /series/volume/case/ with one matching case """

    # setup
    url = case_document.get_frontend_url()
    parsed = parse_xml(case_document.casebody_data.xml)
    case_text = parsed('casebody|casebody').children()[10].text.replace('\xad', '')

    ### can load whitelisted case

    case_document.jurisdiction.whitelisted = True
    case_document.save()

    retrieve_and_check_response_content(client, url, case_text)

    ### can load blacklisted case while logged out, via redirect

    case_document.jurisdiction.whitelisted = False
    case_document.save()

    # first we get redirect to JS page
    retrieve_and_check_response_content(client, url, "Click here to continue", follow=True)

    # POSTing will set our cookies and let the case load
    response = client.post(reverse('set_cookie'), {'not_a_bot': 'yes', 'next': url}, follow=True)
    check_response(response, content_includes=case_text)
    session = client.session
    assert session['case_allowance_remaining'] == settings.API_CASE_DAILY_ALLOWANCE - 1

    # we can now load directly
    response = client.get(url)
    check_response(response, content_includes=case_text)
    session = client.session
    assert session['case_allowance_remaining'] == settings.API_CASE_DAILY_ALLOWANCE - 2

    # can no longer load if quota used up
    session['case_allowance_remaining'] = 0
    session.save()
    response = client.get(url)
    check_response(response)
    assert case_text not in response.content.decode()
    session = client.session
    assert session['case_allowance_remaining'] == 0

    # check daily quota resettest_unlimited_access
    session['case_allowance_last_updated'] -= 60 * 60 * 24 + 1
    session.save()
    response = client.get(url)
    check_response(response, content_includes=case_text)
    session = client.session
    assert session['case_allowance_remaining'] == settings.API_CASE_DAILY_ALLOWANCE - 1

    ### can load normally as logged-in user

    response = auth_client.get(url)
    check_response(response, content_includes=case_text)
    auth_client.auth_user.refresh_from_db()
    assert auth_client.auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 1


@pytest.mark.django_db
def test_case_series_name_redirect(client, case_document):
    """ Test /series/volume/case/ with series redirect when not slugified"""
    cite = case_document.citations[0]
    cite_parts = re.match(r'(\S+)\s+(.*?)\s+(\S+)$', cite.cite).groups()

    # series is not slugified, expect redirect
    response = client.get(
        reverse('citation', args=[cite_parts[1], cite_parts[0], cite_parts[2]], host='cite'))
    check_response(response, status_code=302)

    response = client.get(
        reverse('citation', args=[cite_parts[1], cite_parts[0], cite_parts[2]], host='cite'), follow=True)
    check_response(response)

    # series redirect works with case_id
    response = client.get(
        reverse('citation', args=[cite_parts[1], cite_parts[0], cite_parts[2], case_document.id], host='cite'))
    check_response(response, status_code=302)

    response = client.get(
        reverse('citation', args=[cite_parts[1], cite_parts[0], cite_parts[2]], host='cite'), follow=True)
    check_response(response)


def get_schema(response):
    soup = BeautifulSoup(response.content.decode(), 'html.parser')
    scripts = soup.find_all('script', {'type': 'application/ld+json'})
    assert len(scripts) == 1
    script = scripts[0]
    return json.loads(script.text)

@pytest.mark.django_db
def test_schema_in_case(client, case_document):
    # I moved much of this functionality into separate functions with the @retry decorator because
    # it might take a few seconds for the new data to be available in the API after the record is saved
    @retry(tries=10, delay=1)
    def check_wl_schema(client, case_document, content_includes, url):
        response = client.get(url)
        check_response(response, content_includes=content_includes)

        schema = get_schema(response)
        assert schema["headline"] == case_document.name_abbreviation
        assert schema["author"]["name"] == case_document.court.name

        # if case is whitelisted, extra info about inaccessibility is not needed
        # https://developers.google.com/search/docs/data-types/paywalled-content
        assert "hasPart" not in schema

    @retry(tries=10, delay=1)
    def check_bl_schema(client, case_document, content_includes, url):
        response = client.post(reverse('set_cookie'), {'not_a_bot': 'yes', 'next': url}, follow=True)
        check_response(response, content_includes=content_includes)
        schema = get_schema(response)
        assert schema["headline"] == case_document.name_abbreviation
        assert schema["author"]["name"] == case_document.court.name

        # if case is blacklisted, we include more data
        assert "hasPart" in schema
        assert schema["hasPart"]["isAccessibleForFree"] == 'False'

    # setup
    url = case_document.get_frontend_url()
    parsed = parse_xml(case_document.casebody_data.xml)
    case_text = parsed('casebody|casebody').children()[10].text.replace('\xad', '')

    ### whitelisted case

    case_document.jurisdiction.whitelisted = True
    case_document.save()

    check_wl_schema(client, case_document, case_text, url)

    ### blacklisted case

    case_document.jurisdiction.whitelisted = False
    case_document.save()

    check_bl_schema(client, case_document, case_text, url)



@pytest.mark.django_db()
def test_schema_in_case_as_google_bot(client, case_document, monkeypatch):
    @retry(tries=10, delay=1)
    def post_save(client, case_document, case_text):
        response = client.get(case_document.get_frontend_url(), follow=True)
        assert not is_cached(response)

        # show cases anyway
        check_response(response, content_includes=case_text)
        schema = get_schema(response)
        assert schema["headline"] == case_document.name_abbreviation
        assert schema["author"]["name"] == case_document.court.name
        assert "hasPart" in schema
        assert schema["hasPart"]["isAccessibleForFree"] == 'False'
    # setup
    parsed = parse_xml(case_document.casebody_data.xml)
    case_text = parsed('casebody|casebody').children()[10].text.replace('\xad', '')

    def mock_is_google_bot(request):
        return True

    monkeypatch.setattr(helpers, 'is_google_bot', mock_is_google_bot)

    # our bot has seen too many cases!
    session = client.session
    session['case_allowance_remaining'] = 0
    session.save()
    assert session['case_allowance_remaining'] == 0

    case_document.jurisdiction.whitelisted = False
    case_document.save()

    post_save(client, case_document, case_text)




@pytest.mark.django_db()
def test_no_index(auth_client, case_document):
    case_document.no_index = True
    case_document.save()

    retrieve_and_check_response_content(auth_client, case_document.get_frontend_url(),'content="noindex"' )
