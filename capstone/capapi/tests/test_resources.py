from django.test import TestCase
from capapi.resources import *

class ModelTestCase(TestCase):
    def test_format_blacklisted_filename(self):
        case_id = '12345_0001'
        formatted_filename = format_filename(case_id)
        assert settings.CAP_DATA_DIR_VAR in formatted_filename
        assert '_redacted' in formatted_filename

    def test_format_whitelisted_filename(self):
        case_id = '12345_0001'
        formatted_filename = format_filename(case_id, whitelisted=True)
        assert settings.WHITELISTED_DATA_DIR in formatted_filename
