import re

import pytest
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.utils import timezone

from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse

from capapi.models import CapUser
from capapi.tests.helpers import check_response, is_cached


### register, verify email address, login ###

@pytest.mark.django_db
def test_registration_flow(client, case):

    # can register
    email = 'new_user@gmail.com'
    response = client.post(reverse('register'), {
        'email': email,
        'first_name': 'First',
        'last_name': 'Last',
        'password1': 'Password2',
        'password2': 'Password2',
    })
    check_response(response)
    user = CapUser.objects.get(email=email)
    assert user.first_name == "First"
    assert user.last_name == "Last"
    assert user.check_password("Password2")
    assert user.total_case_allowance == 0

    # new user doesn't have a token yet
    with pytest.raises(Token.DoesNotExist):
        assert user.auth_token

    # can't login without verifying email address
    response = client.post(reverse('login'), {
        'username': user.email,
        'password': 'Password2'
    })
    check_response(response, content_includes="This email is registered but not yet verified")

    # can verify email address
    verify_email = mail.outbox[0].body
    verify_url = re.findall(r'http://\S+', verify_email)[0]
    response = client.get(verify_url)
    check_response(response, content_includes="Thank you for verifying")
    user.refresh_from_db()
    assert user.email_verified
    assert user.auth_token
    assert user.total_case_allowance == settings.API_CASE_DAILY_ALLOWANCE

    # can login with verified email address
    response = client.post(reverse('login'), {
        'username': user.email,
        'password': 'Password2'
    })
    check_response(response, status_code=302)

    # can fetch blacklisted case
    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()
    response = client.get(reverse('casemetadata-detail', kwargs={'id': case.pk}), {'full_case':'true'})
    check_response(response, content_includes="ok")

    # can't register with similar email addresses
    response = client.post(reverse('register'), {
        'email': email.replace('new_user', 'new_user+stuff'),
        'first_name': 'First',
        'last_name': 'Last',
        'password1': 'Password2',
        'password2': 'Password2',
    })
    check_response(response, content_includes="A user with the same email address has already registered.")

@pytest.mark.django_db
def test_login_wrong_password(auth_user, client):
    response = client.post(reverse('login'), {
        'username': auth_user.email,
        'password': 'fake'
    })
    check_response(response)
    assert "Please enter a correct email and password." in response.content.decode()

@pytest.mark.django_db
def test_resend_verification(client, mailoutbox):
    # create new user
    response = client.post(reverse('register'), {
        'email': 'new_user@example.com',
        'first_name': 'First',
        'last_name': 'Last',
        'password1': 'Password2',
        'password2': 'Password2',
    })
    check_response(response)
    assert len(mailoutbox) == 1

    # resend verification
    response = client.post(reverse('resend-verification'), {
        'email': 'new_user@example.com',
    })
    check_response(response)

    # same verification email sent
    assert mailoutbox[0].body == mailoutbox[1].body


### view account details ###

@pytest.mark.django_db
def test_view_user_details(auth_user, auth_client):
    """ User can see their API token """
    response = auth_client.get(reverse('user-details'))
    check_response(response)
    assert b"user_api_key" in response.content
    assert auth_user.get_api_key() in response.content.decode()

    # normal user can see limit
    content = re.sub(r'\s+', ' ', response.content.decode()).strip()
    assert "Unlimited access until" not in content
    total_case_allowance_html = """<span class="user_total_case_allowance form-control form-control-sm"> 500 </span>"""
    assert total_case_allowance_html in content

    # user can't see limit if they have unlimited access
    auth_user.unlimited_access_until = timedelta(hours=24) + timezone.now()
    auth_user.save()
    response = auth_client.get(reverse('user-details'))
    check_response(response)
    content = re.sub(r'\s+', ' ', response.content.decode()).strip()
    assert total_case_allowance_html not in content
    assert "Unlimited access until" in content


### bulk downloads ###

@pytest.mark.django_db
def test_bulk_data_logged_out_list(client):
    response = client.get(reverse('bulk-data'))
    check_response(response)
    content = response.content.decode()
    assert "Arkansas" in content
    assert "Massachusetts" not in content

@pytest.mark.django_db
def test_bulk_data_logged_in_list(auth_client):
    response = auth_client.get(reverse('bulk-data'))
    check_response(response)
    content = response.content.decode()
    assert "Arkansas" in content
    # logged in user still shouldn't see bulk data
    assert "Massachusetts" not in content

@pytest.mark.django_db
def test_bulk_data_unlimited_list(unlimited_auth_client):
    response = unlimited_auth_client.get(reverse('bulk-data'))
    check_response(response)
    content = response.content.decode()
    assert "Arkansas" in content
    assert "Massachusetts" in content

private_zip_url = reverse('bulk-download', kwargs={'public_or_private': 'private', 'jur': 'Massachusetts', 'filename': 'Fake Massachusetts.zip'})
public_zip_url = reverse('bulk-download', kwargs={'public_or_private': 'public', 'jur': 'Illinois', 'filename': 'Fake Illinois.zip'})
def check_zip_response(response):
    check_response(response, content_type='application/zip')
    assert b''.join(response.streaming_content) == b'fake zip content\n'

@pytest.mark.django_db
def test_bulk_data_logged_out_download(client):
    response = client.get(public_zip_url)
    check_zip_response(response)
    assert is_cached(response)
    response = client.get(private_zip_url)
    check_response(response, status_code=403)

@pytest.mark.django_db
def test_bulk_data_logged_in_download(auth_client):
    response = auth_client.get(public_zip_url)
    check_zip_response(response)
    assert is_cached(response)
    response = auth_client.get(private_zip_url)
    check_response(response, status_code=403)

@pytest.mark.django_db
def test_bulk_data_unlimited_download(unlimited_auth_client):
    response = unlimited_auth_client.get(public_zip_url)
    check_zip_response(response)
    assert is_cached(response)
    response = unlimited_auth_client.get(private_zip_url)
    check_zip_response(response)
    assert not is_cached(response)
