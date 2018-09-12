import pytest

from bs4 import BeautifulSoup

from rest_framework.reverse import reverse

from capapi.tests.helpers import check_response



@pytest.mark.django_db
def test_nav(client):
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


