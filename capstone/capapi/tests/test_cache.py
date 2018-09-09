from copy import deepcopy

import pytest
from django.http import SimpleCookie
from django.urls import reverse

from capapi.tests.helpers import is_cached


@pytest.mark.django_db
@pytest.mark.parametrize("view_name, cache_if_logged_out, cache_if_logged_in, get_kwargs", [
    # docs pages are cached for both logged in and logged out
    ("home",                True,   True,  {}),

    # pages with csrf tokens are not cached for logged out or logged in
    ("login",               False,  False,  {}),
    ("register",            False,  False,  {}),

    # login-only pages are cached only for logged out (where they redirect)
    ("user-details",        True,   False,   {}),

    # api views are cached for both logged in and logged out
    ("casemetadata-list",   True,   True,   {}),
    ("casemetadata-list",   True,   True,   {"HTTP_ACCEPT": "text/html"}),

    # api views that depend on the user account are cached only for logged out
    ("casemetadata-list",   True,   False,  {"data": {"full_case": "true"}}),

    # bulk list cacheable only for logged-out users
    ("bulk-data",           True,   False,  {}),

    # bulk downloads are cached if public, or private requested by logged-out users
    ("caseexport-download", True, True,     {"reverse_args": ["fixture_case_export"]}),
    ("caseexport-download", True, False,    {"reverse_args": ["fixture_private_case_export"]}),
])
@pytest.mark.parametrize("client_fixture_name", ["client", "auth_client"])
def test_cache_headers(case, request, settings,
                       client_fixture_name,
                       view_name, cache_if_logged_out, cache_if_logged_in, get_kwargs):

    # set up variables
    get_kwargs = deepcopy(get_kwargs)  # avoid modifying between tests
    settings.SET_CACHE_CONTROL_HEADER = True
    client = request.getfuncargvalue(client_fixture_name)
    cache_expected = cache_if_logged_in if client._credentials else cache_if_logged_out

    # Resolve reverse_args. For example, if we see "fixture_case_export" we will fetch the "case_export" fixture
    # and insert its ID as an argument to reverse().
    reverse_args = get_kwargs.pop('reverse_args', [])
    for i, arg in enumerate(reverse_args):
        if arg.startswith("fixture_"):
            reverse_args[i] = request.getfuncargvalue(arg.split('_', 1)[1]).pk
    url = reverse(view_name, args=reverse_args)

    # see if response is cached
    response = client.get(url, **get_kwargs)
    cache_actual = is_cached(response)

    assert cache_actual == cache_expected, "Checking %s with %s, expected %scached but found %scached." % (
        url,
        client_fixture_name,
        "" if cache_expected else "not ",
        "" if cache_actual else "not ",
    )

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