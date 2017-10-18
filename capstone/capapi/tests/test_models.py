import pytest
from django.conf import settings

from capapi.models import APIToken


@pytest.mark.django_db
def test_update_case_allowance(user):

    # django is doing something funky here with lazy loading
    # so we're subtracting zero for no effect
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE + 0

    user.update_case_allowance(case_count=10)
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 10

@pytest.mark.django_db
def test_authenticate_user(user):
    user.activation_nonce = '123'
    user.save()
    assert user.get_api_key() is None
    user.authenticate_user(activation_nonce=user.activation_nonce)
    assert user.get_api_key() is not None
    assert APIToken.objects.get(user=user)