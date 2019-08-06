from bs4 import BeautifulSoup
from io import BytesIO
import mock
import pytest
from PIL import Image

from django.conf import settings

from capapi.tests.helpers import check_response
from capweb.helpers import reverse, page_image_url
from scripts import update_snippets


@pytest.mark.django_db
def test_nav(client, ingest_case_xml, reporter):
    """
    All our navigation links lead to somewhere 200 Ok
    """
    # this is necessary because some routes need specific snippets now
    update_snippets.update_all()

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
        url = a.get('href')
        if settings.PARENT_HOST in url:
            res = client.get(url)
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


def test_screenshot(client, live_server, settings, ngrammed_cases):
    # set up conditions for /screenshot/ route to work
    settings.SCREENSHOT_FEATURE = True
    settings.DEBUG = True  # so view expects an http url
    live_server_port = live_server.url.rsplit(':', 1)[1]
    with mock.patch('capweb.views._safe_domains', ['case.test:%s' % live_server_port]):

        # url we want a screenshot of -- .graph-container in /trends/?q=the
        target_url = reverse('trends', port=live_server_port).replace(':8000', '') + '?q=the'
        target_selector = '.graph-container'

        # check screenshot
        screenshot_url = page_image_url(target_url, targets=[target_selector], timeout=30)
        response = client.get(screenshot_url)
        check_response(response, content_type="image/png")
        # screenshot size doesn't seem to be consistent across host environments?
        # width, height = Image.open(BytesIO(response.content)).size
        # assert width == 664
        # assert height == 400

        # check fallback screenshot
        screenshot_url = page_image_url(target_url, targets=['.does_not_exist'], timeout=30)
        response = client.get(screenshot_url)
        check_response(response, content_type="image/jpeg")
        # check that we got the default fallback image, api.jpg
        width, height = Image.open(BytesIO(response.content)).size
        assert width == 1200
        assert height == 630
