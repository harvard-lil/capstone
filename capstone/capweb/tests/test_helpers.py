import pytest
import socket
from django.test import RequestFactory
from capweb.helpers import is_google_bot

user_agent_google = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
user_agent_other = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:67.0) Gecko/20100101 Firefox/67.0"


@pytest.mark.django_db
def x_test_is_google_bot_with_dns_lookup(anonymous_user):
    """
    This test is brittle and assumes Google's IP address. It will perform an DNS lookup.

    Ideally, the order of operations would be:
    - headers (ip, user agent) are created
    - request with headers is made
    - anonymous user is assigned, META object is created
    - request is processed, wrap_user is called, request.user.ip_address exists

    However, a lot of necessary middleware is not run.
    So instead, we rely on RequestFactory to create a request with a META object,
    and we set an anoymous_user fixture (that would be created automatically with auth middleware
    """

    request = RequestFactory().get('/')
    request.user = anonymous_user

    # User agent and IP look like Google
    request.META["HTTP_USER_AGENT"] = user_agent_google
    request.user.ip_address = "66.249.66.1"
    assert is_google_bot(request)

    # User agent is not a bot
    request.META["HTTP_USER_AGENT"] = user_agent_other

    assert not is_google_bot(request)

    # User agent looks like a google bot but IP address is not a bot
    request.META["HTTP_USER_AGENT"] = user_agent_google
    request.user.ip_address = "123.456.789"
    assert not is_google_bot(request)


@pytest.mark.django_db
def test_is_google_bot_without_dns_lookup(monkeypatch, anonymous_user):
    """
    Stubbing out DNS lookup, returning a google bot host string.

    """

    def mock_get_googlehost(ip):
        return ["crawl-66-249-66-1.googlebot.com"]

    monkeypatch.setattr(socket, "gethostbyaddr", mock_get_googlehost)
    request = RequestFactory().get('/')
    request.user = anonymous_user

    # User agent and IP look like Google
    request.META["HTTP_USER_AGENT"] = user_agent_google
    request.user.ip_address = "66.249.66.1"
    assert is_google_bot(request)

    # User agent is not a bot
    request.META["HTTP_USER_AGENT"] = user_agent_other
    assert not is_google_bot(request)

    def mock_get_otherhost(ip):
        return ["not-googlebot.com"]

    # User agent looks like a google bot but IP address is not a bot
    monkeypatch.setattr(socket, "gethostbyaddr", mock_get_otherhost)
    request.META["HTTP_USER_AGENT"] = user_agent_google
    request.user.ip_address = "123.456.789"
    assert not is_google_bot(request)
