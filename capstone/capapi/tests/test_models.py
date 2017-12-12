import pytest
from datetime import timedelta

from django.utils import timezone
from django.conf import settings

from capapi.models import APIToken


@pytest.mark.django_db
def test_default_case_allowance(user):
    assert user.total_case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 0
    user.save()
    user.update_case_allowance(case_count=10)
    assert user.case_allowance_remaining == settings.API_CASE_DAILY_ALLOWANCE - 10

@pytest.mark.django_db
def test_custom_case_allowance(user):
    user.total_case_allowance = 1000
    user.case_allowance_remaining = 0
    user.save()
    # set last_updated to yesterday
    user.case_allowance_last_updated = timezone.now() - timedelta(days=1)
    user.save()
    user.update_case_allowance()
    assert user.case_allowance_remaining == user.total_case_allowance

@pytest.mark.django_db
def test_authenticate_user(user):
    user.activation_nonce = '123'
    user.save()
    assert user.get_api_key() is None
    user.authenticate_user(activation_nonce=user.activation_nonce)
    assert user.get_api_key() is not None
    assert APIToken.objects.get(user=user)


