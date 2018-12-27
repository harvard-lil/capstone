import re

import pytest
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.utils import timezone
from rest_framework.authtoken.models import Token

from capapi import api_reverse
from capapi.models import CapUser
from capapi.tests.helpers import check_response
from capweb.helpers import reverse


### register, verify email address, login ###

@pytest.mark.django_db
def test_registration_flow(client, case):

    # can't register without agreeing to TOS
    email = 'new_user@gmail.com'
    register_kwargs = {
        'email': email,
        'first_name': 'First',
        'last_name': 'Last',
        'password1': 'Password2',
        'password2': 'Password2',
        'agreed_to_tos': '',
    }
    response = client.post(reverse('register'), register_kwargs)
    check_response(response, content_includes="This field is required.")

    # can register
    register_kwargs['agreed_to_tos'] = 'on'
    response = client.post(reverse('register'), register_kwargs)
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
    verify_url = re.findall(r'https://\S+', verify_email)[0]
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
    response = client.get(api_reverse('casemetadata-detail', kwargs={'id': case.pk}), {'full_case':'true'})
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
        'agreed_to_tos': 'on',
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
    content = re.sub(r'\s+', ' ', response.content.decode()).strip()
    assert auth_user.get_api_key() in content
    assert "Unlimited access:" not in content
    assert str(auth_user.total_case_allowance) in content

    # user can't see limit if they have unlimited access
    auth_user.unlimited_access = True
    auth_user.unlimited_access_until = timedelta(hours=24) + timezone.now()
    auth_user.save()
    response = auth_client.get(reverse('user-details'))
    check_response(response)
    content = re.sub(r'\s+', ' ', response.content.decode()).strip()
    assert "Unmetered access:" in content


### bulk downloads ###

@pytest.mark.parametrize("client_fixture, can_see_private", [
    ("client", False),
    ("auth_client", False),
    ("unlimited_auth_client", True)
])
@pytest.mark.django_db
def test_bulk_data_list(request, case_export, private_case_export, client_fixture, can_see_private):
    client = request.getfixturevalue(client_fixture)
    public_url = api_reverse('caseexport-download', args=[case_export.pk])
    private_url = api_reverse('caseexport-download', args=[private_case_export.pk])

    response = client.get(reverse('bulk-download'))
    check_response(response)
    content = response.content.decode()
    assert public_url in content
    if can_see_private:
        assert private_url in content
    else:
        assert private_url not in content

def check_zip_response(response):
    check_response(response, content_type='application/zip')
    assert b''.join(response.streaming_content) == b'fake zip content'

@pytest.mark.parametrize("client_fixture, export_fixture, status_code", [
    ("client", "case_export", 200),
    ("client", "private_case_export", 401),
    ("auth_client", "case_export", 200),
    ("auth_client", "private_case_export", 403),
    ("unlimited_auth_client", "case_export", 200),
    ("unlimited_auth_client", "private_case_export", 200),
])
@pytest.mark.django_db
def test_case_export_download(request, client_fixture, export_fixture, status_code):
    client = request.getfixturevalue(client_fixture)
    export = request.getfixturevalue(export_fixture)
    response = client.get(api_reverse('caseexport-download', args=[export.pk]))
    if status_code == 200:
        check_zip_response(response)
    else:
        check_response(response, status_code=status_code)


### research access request ###

@pytest.mark.django_db
def test_unaffiliated_research_access_request(auth_client, mailoutbox):
    # can view form
    response = auth_client.get(reverse('unaffiliated-research-request'))
    check_response(response)

    # can submit form
    values = {
        'name': 'First Last',
        'email': 'foo@example.com',
        'area_of_interest': 'Foo Area of Interest'
    }
    response = auth_client.post(reverse('unaffiliated-research-request'), values)
    check_response(response, status_code=302)
    assert response.url == reverse('unaffiliated-research-request-success')

    # check created request and email message
    research_request = auth_client.auth_user.research_requests.first()
    message = mailoutbox[0].body
    for k, v in values.items():
        assert getattr(research_request, k) == v
        assert v in message

@pytest.mark.django_db
def test_harvard_research_access_request(auth_client, mailoutbox):
    user = auth_client.auth_user

    # viewing form with non-harvard email doesn't work
    response = auth_client.get(reverse('harvard-research-request-intro'), follow=True)
    check_response(response, content_includes="You are not currently using a harvard.edu email address")
    response = auth_client.get(reverse('harvard-research-request'), follow=True)
    check_response(response, content_includes="You are not currently using a harvard.edu email address")

    # viewing as harvard email does work
    user.email = 'foo@harvard.edu'
    user.save()
    response = auth_client.get(reverse('harvard-research-request'))
    check_response(response, content_includes="Sign Agreement")

    # can submit form
    values = {
        'name': 'First Last',
        'title': 'Title',
        'area_of_interest': 'Area of Interest'
    }
    response = auth_client.post(reverse('harvard-research-request'), values)
    check_response(response, status_code=302)
    assert response.url == reverse('harvard-research-request-success')

    # check created contract and email message
    research_request = user.harvard_contracts.first()
    message = mailoutbox[0].body
    for k, v in values.items():
        assert getattr(research_request, k) == v
        assert v in message
    user.refresh_from_db()
    assert user.harvard_access is True

@pytest.mark.django_db
def test_affiliated_research_access_request(auth_client, contract_approver_auth_client, mailoutbox):
    user = auth_client.auth_user

    # can view form
    response = auth_client.get(reverse('affiliated-research-request'))
    check_response(response)

    # can submit form
    values = {
        'name': 'First Last',
        'email': 'will_be_ignored@example.com',
        'institution': 'Foo Institution',
        'title': 'Foo Title',
        'area_of_interest': 'Foo Area of Interest'
    }
    response = auth_client.post(reverse('affiliated-research-request'), values)
    check_response(response, status_code=302)
    assert response.url == reverse('affiliated-research-request-success')
    contract = user.research_contracts.first()
    assert contract

    # can review contract
    message = mailoutbox[0].body
    approve_url = message.split("deny this application at ")[1].split()[0]
    response = contract_approver_auth_client.get(approve_url)
    check_response(response, content_includes=values['name'])

    # can deny contract
    response = contract_approver_auth_client.post(approve_url, {
        'contract_id': contract.id,
        'deny': 'true'
    })
    check_response(response, content_includes="%s denied" % values['name'])
    contract.refresh_from_db()
    assert contract.status == 'denied'
    user.refresh_from_db()
    assert not user.unlimited_access_in_effect()
    message = mailoutbox[1].body
    assert "has been denied" in message

    # can approve contract
    contract.status = 'pending'
    contract.save()
    response = contract_approver_auth_client.post(approve_url, {
        'contract_id': contract.id,
        'approve': 'true'
    })
    check_response(response, content_includes="%s approved" % values['name'])
    contract.refresh_from_db()
    assert contract.status == 'approved'
    assert contract.approver_signature_date
    assert contract.approver == contract_approver_auth_client.auth_user
    user.refresh_from_db()
    assert user.unlimited_access_in_effect()

    # check created contract and email message
    message = mailoutbox[2].body
    values['email'] = user.email
    for k, v in values.items():
        assert getattr(contract, k) == v
        assert v in message
        assert v in contract.contract_html
