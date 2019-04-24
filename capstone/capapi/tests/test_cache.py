from copy import deepcopy

import pytest
from django.http import SimpleCookie

from capapi.resources import api_reverse  # noqa -- this is dynamically used by test_cache_headers
from capapi.tests.helpers import is_cached, check_response
from capweb.helpers import reverse


@pytest.mark.django_db
@pytest.mark.parametrize("view_name, cache_clients, get_kwargs", [
    # docs pages are cached for both logged in and logged out, but not for token auth
    ("home",                ["client", "auth_client"],                        {}),

    # pages with csrf tokens are not cached for logged out or logged in
    ("login",               [],                                               {}),
    ("register",            [],                                               {}),

    # login-only pages are not cached for either (because we don't cache redirects for logged-out user)
    ("user-details",        [],                                               {}),

    # api views are cached for both logged in and logged out
    ("casemetadata-list",   ["client", "auth_client", "token_auth_client"],   {"reverse_func": "api_reverse"}),
    ("casemetadata-list",   ["client", "auth_client", "token_auth_client"],   {"HTTP_ACCEPT": "text/html", "reverse_func": "api_reverse"}),

    # api views that depend on the user account are cached only for logged out
    ("casemetadata-list",   ["client"],                                       {"data": {"full_case": "true"}, "reverse_func": "api_reverse"}),

    # bulk list cacheable only for logged-out users
    ("bulk-download",       ["client"],                                       {}),

    # bulk downloads are cached if public
    ("caseexport-download", ["client", "auth_client", "token_auth_client"],   {"reverse_args": ["fixture_case_export"], "reverse_func": "api_reverse"}),
    # bulk downloads are not cached if private
    ("caseexport-download", [],                                               {"reverse_args": ["fixture_private_case_export"], "reverse_func": "api_reverse"}),
])
@pytest.mark.parametrize("client_fixture_name", ["client", "auth_client", "token_auth_client"])
def test_cache_headers(case, request, settings,
                       client_fixture_name,
                       view_name, cache_clients, get_kwargs):

    # set up variables
    get_kwargs = deepcopy(get_kwargs)  # avoid modifying between tests
    settings.SET_CACHE_CONTROL_HEADER = True
    client = request.getfuncargvalue(client_fixture_name)

    # Resolve reverse_args. For example, if we see "fixture_case_export" we will fetch the "case_export" fixture
    # and insert its ID as an argument to reverse().
    reverse_args = get_kwargs.pop('reverse_args', [])
    for i, arg in enumerate(reverse_args):
        if arg.startswith("fixture_"):
            reverse_args[i] = request.getfuncargvalue(arg.split('_', 1)[1]).pk

    # reverse from the view name, using get_kwargs['reverse_func'] or reverse() by default
    reverse_func = get_kwargs.pop('reverse_func', 'reverse')
    reverse_func = globals()[reverse_func]
    url = reverse_func(view_name, args=reverse_args)

    # see if response is cached
    response = client.get(url, **get_kwargs)
    cache_actual = is_cached(response)

    cache_expected = client_fixture_name in cache_clients
    assert cache_actual == cache_expected, "Checking %s with %s, expected %scached but found %scached." % (
        url,
        client_fixture_name,
        "" if cache_expected else "not ",
        "" if cache_actual else "not ",
    )

@pytest.mark.django_db
def test_cache_case_cite(client, case, settings):
    """ Single-case cite.case.law page should be cached only if case is whitelisted. """
    settings.SET_CACHE_CONTROL_HEADER = True
    url = case.get_readable_url()

    # whitelisted case is cached
    case.jurisdiction.whitelisted = True
    case.jurisdiction.save()
    response = client.get(url)
    check_response(response, content_includes=case.name)
    assert is_cached(response)

    # non-whitelisted case not cached
    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()
    response = client.post(reverse('set_cookie'), {'not_a_bot': 'yes', 'next': url}, follow=True)
    check_response(response, content_includes=case.name)
    assert not is_cached(response)

@pytest.mark.django_db
def test_cache_headers_with_bad_auth(client, case, settings):
    settings.SET_CACHE_CONTROL_HEADER = True

    # visiting homepage when logged out is cached ...
    response = client.get(reverse('home'))
    assert is_cached(response)

    # ... but visiting with a bad Authorization header is not cached
    client.credentials(HTTP_AUTHORIZATION='Token fake')
    response = client.get(reverse('home'))
    assert not is_cached(response)

    # ... and visiting with a bad session cookie is not cached
    client.credentials()
    client.cookies = SimpleCookie({settings.SESSION_COOKIE_NAME: 'fake'})
    response = client.get(reverse('home'))
    assert not is_cached(response)