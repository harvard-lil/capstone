from django.test import TestCase
from capi_project.models import Case, CaseUser

from rest_framework.test import APIRequestFactory
from django.test import Client
from django.conf import settings
from datetime import timedelta
import json

class CaseTestCase(TestCase):
    def setUp(self):
        user = CaseUser(email="boblawblaw@lawblog.com", first_name="Bob", last_name="Lawblaw")
        user.set_password("test-password")
        user.save()

    def test_case_permissions(self):
        user = CaseUser.objects.get(email="boblawblaw@lawblog.com")
        assert user.case_allowance == settings.CASE_DAILY_ALLOWANCE
        print "testing if updating case allowance daily is working"
        user.case_allowance = 200
        user.case_allowance_last_updated =  user.case_allowance_last_updated - timedelta(hours=settings.CASE_EXPIRE_HOURS)
        user.save()
        user.update_case_allowance()
        assert user.case_allowance == settings.CASE_DAILY_ALLOWANCE

    def authenticate_user(self):
        user = CaseUser.objects.get(email="boblawblaw@lawblog.com")
        user.activation_nonce = "123"
        user.key_expires = timedelta.now()
        user.save()
        user.authenticate_user()
        assert user.is_authenticated()
        assert user.is_active
        token = user.get_api_key()
        assert len(token) > 5
