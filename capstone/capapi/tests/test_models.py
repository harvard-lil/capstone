import pytest
from datetime import timedelta

from django.utils import timezone
from django.conf import settings

from capapi.models import APIToken


@pytest.mark.django_db
def test_default_case_allowance(api_user):
    assert api_user.total_case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 0
    api_user.save()
    api_user.update_case_allowance(case_count=10)
    assert api_user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 10

@pytest.mark.django_db
def test_custom_case_allowance(api_user):
    api_user.total_case_allowance = 1000
    api_user.case_allowance_remaining = 0
    api_user.save()
    # set last_updated to yesterday
    api_user.case_allowance_last_updated = timezone.now() - timedelta(days=1)
    api_user.save()
    api_user.update_case_allowance()
    assert api_user.case_allowance_remaining == api_user.total_case_allowance

@pytest.mark.django_db
def test_authenticate_api_user(api_user):
    api_user.activation_nonce = '123'
    api_user.save()
    assert api_user.get_api_key() is None
    api_user.authenticate_user(activation_nonce=api_user.activation_nonce)
    assert api_user.get_api_key() is not None
    assert APIToken.objects.get(user=api_user)


