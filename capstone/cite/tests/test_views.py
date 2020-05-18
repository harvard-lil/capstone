import re
import json
from datetime import timedelta
from pathlib import Path

import mock
import pytest
from bs4 import BeautifulSoup

from django.utils import timezone

from capapi.tests.helpers import check_response, is_cached
from capweb.helpers import reverse


def full_url(document):
    return "{}{}".format(reverse('cite_home'), document.frontend_url.replace('/', '', 1))

@pytest.mark.django_db
def test_home(client, django_assert_num_queries, reporter):
    """ Test / """
    with django_assert_num_queries(select=2):
        response = client.get(reverse('cite_home', host='cite'))
    check_response(response, content_includes=reporter.full_name)


@pytest.mark.django_db
def test_series(client, django_assert_num_queries, volume_metadata_factory):
    """ Test /series/ """

    # make sure we correctly handle multiple reporters with same slug
    volume_1, volume_2 = [volume_metadata_factory(
        reporter__short_name='Mass.',
        reporter__short_name_slug='mass',
    ) for _ in range(2)]
    response = client.get(reverse('series', args=['mass'], host='cite'))
    check_response(response)
    content = response.content.decode()
    for vol in (volume_1, volume_2):
        assert vol.volume_number in content
        assert vol.reporter.full_name in content

    # make sure we redirect if series is not slugified
    response = client.get(reverse('series', args=['Mass.'], host='cite'))
    check_response(response, status_code=302)
    response = client.get(reverse('series', args=['mass'], host='cite'), follow=True)
    check_response(response, status_code=200)
    
    # make sure we get 404 if bad series input
    response = client.get(reverse('series', args=['*'], host='cite'))
    check_response(response, status_code=404)


@pytest.mark.django_db
def test_volume(client, django_assert_num_queries, case_factory, elasticsearch):
    """ Test /series/volume/ """
    cases = [case_factory(
        volume__reporter__full_name='Massachusetts%s' % i,
        volume__reporter__short_name='Mass.',
        volume__reporter__short_name_slug='mass',
        volume__volume_number='1',
        volume__volume_number_slug='1',
    ) for i in range(3)]

    with django_assert_num_queries(select=1):
        response = client.get(reverse('volume', args=['mass', '1'], host='cite'))
    check_response(response)

    content = response.content.decode()
    for case in cases:
        assert case.reporter.full_name in content
        assert case.citations.first().cite in content

    # make sure we redirect if reporter name / series is not slugified
    response = client.get(reverse('volume', args=['Mass.', '1'], host='cite'))
    check_response(response, status_code=302)
    response = client.get(reverse('volume', args=['Mass.', '1'], host='cite'), follow=True)
    check_response(response, status_code=200)


@pytest.mark.django_db
def test_case_not_found(client, django_assert_num_queries, elasticsearch):
    """ Test /series/volume/case/ not found """
    with django_assert_num_queries(select=1):
        response = client.get(reverse('citation', args=['fake', '123', '456'], host='cite'))
    check_response(response, content_includes='Citation "123 Fake 456" was not found')


@pytest.mark.django_db
def test_cases_multiple(client, django_assert_num_queries, case_factory, elasticsearch):
    """ Test /series/volume/case/ with multiple matching cases """
    three_cases = [case_factory(
        jurisdiction__whitelisted=True,
        citations__type='official',
        citations__cite='23 Ill. App. 19',
        citations__normalized_cite='23illapp19'
    ) for i in range(3)]
    first_case = three_cases[0]

    response = client.get(reverse('citation', args=['ill-app', '23', '19'], host='cite'), follow=True)

    check_response(response, content_includes='Multiple cases match')
    content = response.content.decode()
    for case in three_cases:
        assert case.name_abbreviation in content

    # load one of the results
    response = client.get(reverse('citation', args=['ill-app', '23', '19', first_case.id], host='cite'))
    check_response(response)


@pytest.mark.django_db
@pytest.mark.parametrize('response_type', ['html', 'pdf'])
def test_single_case(client, auth_client, case_factory, elasticsearch, response_type, django_assert_num_queries, settings):
    """ Test /series/volume/case/ with one matching case """

    settings.CASE_PDF_FEATURE = True

    # set up for viewing html or pdf
    case_text = "Case HTML"
    unrestricted_case = case_factory(jurisdiction__whitelisted=True, body_cache__html=case_text, first_page_order=2, last_page_order=2)
    restricted_case = case_factory(jurisdiction__whitelisted=False, body_cache__html=case_text, first_page_order=2, last_page_order=2)
    if response_type == 'pdf':
        case_text = "Page 2"
        unrestricted_url = unrestricted_case.get_pdf_url()
        url = restricted_case.get_pdf_url()
        content_type = 'application/pdf'
    else:
        unrestricted_url = full_url(unrestricted_case)
        url = full_url(restricted_case)
        content_type = None

    ### can load whitelisted case
    with django_assert_num_queries(select=2):
        check_response(client.get(unrestricted_url), content_includes=case_text, content_type=content_type)

    ### can load blacklisted case while logged out, via redirect

    # first we get redirect to JS page
    check_response(client.get(url, follow=True), content_includes="Click here to continue")

    # POSTing will set our cookies and let the case load
    response = client.post(reverse('set_cookie'), {'not_a_bot': 'yes', 'next': url}, follow=True)
    check_response(response, content_includes=case_text, content_type=content_type)
    session = client.session
    assert session['case_allowance_remaining'] == settings.API_CASE_DAILY_ALLOWANCE - 1

    # we can now load directly
    response = client.get(url)
    check_response(response, content_includes=case_text, content_type=content_type)
    session = client.session
    assert session['case_allowance_remaining'] == settings.API_CASE_DAILY_ALLOWANCE - 2

    # can no longer load if quota used up
    session['case_allowance_remaining'] = 0
    session.save()
    response = client.get(url)
    if response_type == 'pdf':
        assert response.status_code == 302  # PDFs redirect back to HTML version if quota exhausted
    else:
        check_response(response)
        assert case_text not in response.content.decode()
    session = client.session
    assert session['case_allowance_remaining'] == 0

    # check daily quota reset
    session['case_allowance_last_updated'] -= 60 * 60 * 24 + 1
    session.save()
    response = client.get(url)
    check_response(response, content_includes=case_text, content_type=content_type)
    session = client.session
    assert session['case_allowance_remaining'] == settings.API_CASE_DAILY_ALLOWANCE - 1

    ### can load normally as logged-in user

    response = auth_client.get(url)
    check_response(response, content_includes=case_text, content_type=content_type)
    auth_client.auth_user.refresh_from_db()
    assert auth_client.auth_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 1


@pytest.mark.django_db
def test_case_series_name_redirect(client, unrestricted_case, elasticsearch):
    """ Test /series/volume/case/ with series redirect when not slugified"""
    cite = unrestricted_case.citations.first()
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
        reverse('citation', args=[cite_parts[1], cite_parts[0], cite_parts[2], unrestricted_case.id], host='cite'))
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
def test_schema_in_case(client, restricted_case, unrestricted_case, elasticsearch):

    ### whitelisted case

    response = client.get(full_url(unrestricted_case))
    check_response(response, content_includes=unrestricted_case.body_cache.html)

    schema = get_schema(response)
    assert schema["headline"] == unrestricted_case.name_abbreviation
    assert schema["author"]["name"] == unrestricted_case.court.name

    # if case is whitelisted, extra info about inaccessibility is not needed
    # https://developers.google.com/search/docs/data-types/paywalled-content
    assert "hasPart" not in schema

    ### blacklisted case

    response = client.post(reverse('set_cookie'), {'not_a_bot': 'yes', 'next': full_url(restricted_case)}, follow=True)
    check_response(response, content_includes=restricted_case.body_cache.html)
    schema = get_schema(response)
    assert schema["headline"] == restricted_case.name_abbreviation
    assert schema["author"]["name"] == restricted_case.court.name

    # if case is blacklisted, we include more data
    assert "hasPart" in schema
    assert schema["hasPart"]["isAccessibleForFree"] == 'False'


@pytest.mark.django_db()
def test_schema_in_case_as_google_bot(client, restricted_case, elasticsearch):

    # our bot has seen too many cases!
    session = client.session
    session['case_allowance_remaining'] = 0
    session.save()
    assert session['case_allowance_remaining'] == 0

    with mock.patch('cite.views.is_google_bot', lambda request: True):
        response = client.get(full_url(restricted_case), follow=True)
    assert not is_cached(response)

    # show cases anyway
    check_response(response, content_includes=restricted_case.body_cache.html)
    schema = get_schema(response)
    assert schema["headline"] == restricted_case.name_abbreviation
    assert schema["author"]["name"] == restricted_case.court.name
    assert "hasPart" in schema
    assert schema["hasPart"]["isAccessibleForFree"] == 'False'


@pytest.mark.django_db()
def test_no_index(auth_client, case_factory, elasticsearch):
    case = case_factory(no_index=True)
    check_response(auth_client.get(full_url(case)), content_includes='content="noindex"')


@pytest.mark.django_db()
def test_robots(client, case):
    case_string = "Disallow: %s" % case.frontend_url

    # default version is empty:
    url = reverse('robots', host='cite')
    response = client.get(url)
    check_response(response, content_type="text/plain", content_includes='User-agent: *', content_excludes=case_string)

    # case with robots_txt_until in future is included:
    case.no_index = True
    case.robots_txt_until = timezone.now() + timedelta(days=1)
    case.save()
    check_response(client.get(url), content_type="text/plain", content_includes=case_string)

    # case with robots_txt_until in past is excluded:
    case.robots_txt_until = timezone.now() - timedelta(days=1)
    case.save()
    response = client.get(url)
    check_response(response, content_type="text/plain", content_includes='User-agent: *', content_excludes=case_string)


@pytest.mark.django_db
def test_geolocation_log(client, unrestricted_case, elasticsearch, settings, caplog):
    """ Test state-level geolocation logging in case browser """
    if not Path(settings.GEOIP_PATH).exists():
        # only test geolocation if database file is available
        return
    settings.GEOLOCATION_FEATURE = True
    check_response(client.get(full_url(unrestricted_case), HTTP_X_FORWARDED_FOR='128.103.1.1'))
    assert "Someone from Massachusetts, United States read a case" in caplog.text
