from datetime import datetime, timedelta

from django.test import TestCase
from django.conf import settings
import pytz

from capapi.models import CaseUser
import capapi.tests.helpers as helpers


class UserTestCase(TestCase):
    def setUp(self):
        helpers.setup_user(id=1, email="boblawblaw@lawblog.com", first_name="Bob", last_name="Lawblaw", password="unique_password")
        helpers.setup_authenticated_user(id=2, email="authentic_boblawblaw@lawblog.com", first_name="Authentic-Bob", last_name="Lawblaw", password="unique_authentic_password")

    def test_case_permissions(self):
        user = CaseUser.objects.get(email="boblawblaw@lawblog.com")
        assert user.case_allowance == settings.CASE_DAILY_ALLOWANCE
        user.case_allowance = 200
        user.case_allowance_last_updated = user.case_allowance_last_updated - timedelta(hours=settings.CASE_EXPIRE_HOURS)
        user.save()
        user.update_case_allowance()
        assert user.case_allowance == settings.CASE_DAILY_ALLOWANCE

    def test_authenticate_user(self):
        user = CaseUser.objects.get(email="boblawblaw@lawblog.com")
        user.activation_nonce = "123"
        user.key_expires = datetime.now(pytz.utc)
        user.save()
        user.authenticate_user(activation_nonce=user.activation_nonce)
        assert user.is_active
        token = user.get_api_key()
        assert len(token) > 5

    def test_authenticated_user(self):
        user = CaseUser.objects.get(email="authentic_boblawblaw@lawblog.com")
        assert user.is_active
        assert user.is_authenticated

    def test_unauthenticated_user(self):
        user = CaseUser(email="sketchy@gmail.com", first_name="Don't", last_name="Trust")
        token = user.get_api_key()
        assert token is None

    def test_case_allowance_time_update(self):
        user = CaseUser.objects.get(id=2)
        assert user.case_allowance_last_updated is not None
        old_case_allowance_time = user.case_allowance_last_updated
        user.update_case_allowance()
        assert user.case_allowance_last_updated == old_case_allowance_time
        user.case_allowance_last_updated -= timedelta(hours=settings.CASE_EXPIRE_HOURS)
        user.save()
        old_case_allowance_time = user.case_allowance_last_updated
        user.update_case_allowance()
        assert user.case_allowance_last_updated > old_case_allowance_time
        case_allowance_time_remaining = 5
        user.case_allowance_last_updated -= timedelta(hours=settings.CASE_EXPIRE_HOURS - case_allowance_time_remaining)
        user.save()
        assert int(user.get_case_allowance_update_time_remaining()[0]) > 3
