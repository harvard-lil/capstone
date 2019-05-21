import pytest
from capweb.views import subscribe
from capweb.helpers import reverse
from capapi.models import MailingList
from django.test import RequestFactory

@pytest.mark.django_db
def test_subscribe_get():
    path = reverse('subscribe')
    request = RequestFactory().get(path)
    with pytest.raises(Exception, match='GET requests not allowed with this path.'):
        subscribe(request)

@pytest.mark.django_db
def test_subscribe(mailoutbox):
    assert len(mailoutbox) == 0
    assert MailingList.objects.count() == 0
    path = reverse('subscribe')
    data = {'email': 'joe@aol.com'}
    request = RequestFactory().post(path, data)
    subscribe(request)
    assert MailingList.objects.all()[0].email == 'joe@aol.com'
    assert len(mailoutbox) == 1

@pytest.mark.django_db
def test_reject_duplicate_subscribe():
    path = reverse('subscribe')
    data = {'email': 'joe@aol.com'}
    request = RequestFactory().post(path, data)
    original = subscribe(request)
    duplicate = subscribe(request)

    assert original.status_code == 302
    assert original.url.endswith('subscribe-success/')

    assert duplicate.status_code == 200
    assert b'You&#39;re already subscribed.' in duplicate.content

