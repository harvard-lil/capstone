import re

import pytest
from django.core import mail
from rest_framework.reverse import reverse

from capapi.models import SiteLimits, CapUser
from capapi.tasks import daily_site_limit_reset_and_report
from capapi.tests.helpers import check_response


@pytest.mark.django_db
def test_site_limits(client, auth_client, case, mailoutbox):

    ### registration limit ###

    # set signups per day to zero, downloads per day to one
    site_limits = SiteLimits.get()
    site_limits.daily_signup_limit = 0
    site_limits.daily_download_limit = 1
    site_limits.save()

    # register
    email = 'new_user@gmail.com'
    response = client.post(reverse('register'), {
        'email': email,
        'first_name': 'First',
        'last_name': 'Last',
        'password1': 'Password2',
        'password2': 'Password2',
    })
    user = CapUser.objects.get(email=email)

    # verify email address
    verify_email = mail.outbox[0].body
    verify_url = re.findall(r'http://\S+', verify_email)[0]
    response = client.get(verify_url)
    check_response(response, content_includes="Thank you for verifying")
    user.refresh_from_db()
    assert user.email_verified
    assert user.auth_token

    # verified user still has 0 limit
    assert user.total_case_allowance == 0

    ### case download limit ###

    # create blacklisted case
    case.jurisdiction.whitelisted = False
    case.jurisdiction.save()

    # can fetch one case
    response = auth_client.get(reverse('casemetadata-detail', kwargs={'id': case.pk}), {'full_case':'true'})
    result = response.json()
    assert result['casebody']['status'] == 'ok'

    # cannot fetch second case
    response = auth_client.get(reverse('casemetadata-detail', kwargs={'id': case.pk}), {'full_case':'true'})
    result = response.json()
    assert result['casebody']['status'] == 'error_sitewide_limit_exceeded'

    ### tracking ###

    # site_limits updated
    site_limits.refresh_from_db()
    assert site_limits.daily_signups == 1
    assert site_limits.daily_downloads == 1

    ### reporting ###

    daily_site_limit_reset_and_report.apply()
    site_limits.refresh_from_db()
    assert site_limits.daily_signups == 0
    assert site_limits.daily_downloads == 0
    last_mail = mailoutbox[-1]
    assert last_mail.subject == 'CAP daily usage: 1 registered users, 1 blacklisted downloads'


