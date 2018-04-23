import re

import pytest
from django.core import mail
from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse

from capapi.models import CapUser
from capapi.tests.helpers import check_response


### register, verify email address, login ###

@pytest.mark.django_db
def test_registration_flow(client, case):

    # can register
    response = client.post(reverse('register'), {
        'email': 'new_user@example.com',
        'first_name': 'First',
        'last_name': 'Last',
        'password1': 'Password2',
        'password2': 'Password2',
    })
    check_response(response)
    user = CapUser.objects.get(email='new_user@example.com')
    assert user.first_name == "First"
    assert user.last_name == "Last"
    assert user.check_password("Password2")

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

    # can login with verified email address
    response = client.post(reverse('login'), {
        'username': user.email,
        'password': 'Password2'
    })
    check_response(response, status_code=302)

    # can't fetch blacklisted case yet
    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()
    response = client.get(reverse('casemetadata-detail', kwargs={'id': case.pk}), {'full_case':'true'})
    check_response(response, content_includes="error_limit_exceeded")


@pytest.mark.django_db
def test_login_wrong_password(auth_user, client):
    response = client.post(reverse('login'), {
        'username': auth_user.email,
        'password': 'fake'
    })
    check_response(response)
    assert "Please enter a correct email and password." in response.content.decode()

@pytest.mark.django_db
def test_resend_verification(client):
    # create new user
    response = client.post(reverse('register'), {
        'email': 'new_user@example.com',
        'first_name': 'First',
        'last_name': 'Last',
        'password1': 'Password2',
        'password2': 'Password2',
    })
    check_response(response)
    assert len(mail.outbox) == 1

    # resend verification
    response = client.post(reverse('resend-verification'), {
        'email': 'new_user@example.com',
    })
    check_response(response)

    # same verification email sent
    assert mail.outbox[0].body == mail.outbox[1].body


### view account details ###

@pytest.mark.django_db
def test_view_user_details(auth_user, auth_client):
    """ User can see their API token """
    response = auth_client.get(reverse('user-details'))
    check_response(response)
    assert b"user_api_key" in response.content
    assert auth_user.get_api_key() in response.content.decode()