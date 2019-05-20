import pytest
from django.test import RequestFactory
from capweb.helpers import is_google_bot


@pytest.mark.django_db
def x_test_is_google_bot():
    # this test will perform a DNS lookup
    request = RequestFactory().get("/")
    request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    request.META["REMOTE_ADDR"] = "66.249.66.1"
    assert is_google_bot(request)

    request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:67.0) Gecko/20100101 Firefox/67.0"
    assert not is_google_bot(request)
