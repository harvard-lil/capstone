import pytest

from bs4 import BeautifulSoup

from django.conf import settings

from capapi.tests.helpers import check_response
from capweb.helpers import reverse


@pytest.mark.django_db
def test_nav(client, case, reporter):
    """
    All our navigation links lead to somewhere 200 Ok
    """
    response = client.get(reverse('home'))
    check_response(response)
    soup = BeautifulSoup(response.content.decode(), 'html.parser')

    dropdown_item = soup.find_all('a', {'class': 'dropdown-item'})
    for a in dropdown_item:
        res = client.get(a.get('href'))
        check_response(res)

    nav_links = soup.find_all('a', {'class': 'nav-link'})
    for a in nav_links:
        res = client.get(a.get('href'))
        check_response(res)


@pytest.mark.django_db
def test_footer(client):
    """
    All our footer links lead to somewhere 200 Ok
    """
    response = client.get(reverse('home'))
    soup = BeautifulSoup(response.content.decode(), 'html.parser')
    anchors = soup.find('footer').find_all('a')
    for a in anchors:
        res = client.get(a.get('href'))
        check_response(res)


@pytest.mark.django_db
def test_contact(client, auth_client):
    response = client.get(reverse('contact'))
    soup = BeautifulSoup(response.content.decode(), 'html.parser')
    email = soup.find('a', {'class': 'contact_email'})
    assert email.get('href').split("mailto:")[1] == settings.DEFAULT_FROM_EMAIL
    assert not soup.find('input', {'id': 'id_email'}).get('value')

    response = auth_client.get(reverse('contact'))
    soup = BeautifulSoup(response.content.decode(), 'html.parser')
    assert soup.find('input', {'id': 'id_email'}).get('value') == auth_client.auth_user.email
