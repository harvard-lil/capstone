import pytest
from django.conf import settings
from capweb.helpers import reverse
from capapi.tests.helpers import check_response, is_cached

settings.LABS = True

@pytest.mark.django_db
def test_labs_page(client):
    response = client.get(reverse('labs:labs'))
    check_response(response, content_includes="CAP LABS")

