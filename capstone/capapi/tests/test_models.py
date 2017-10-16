import pytest
from django.conf import settings

from test_data.factories import *


@pytest.mark.django_db
def test_update_case_allowance():
    user = APIUserFactory.create()
    # django is doing something funky here with lazy loading
    # so we're subtracting zero for no effect
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE + 0

    user.update_case_allowance(case_count=10)
    assert user.case_allowance == settings.API_CASE_DAILY_ALLOWANCE - 10
