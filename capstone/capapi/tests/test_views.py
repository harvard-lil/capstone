import re
import pytest
from capapi.tests.helpers import check_response
from django.conf import settings


@pytest.mark.django_db
def test_get_docs_urls(client, jurisdiction, case, reporter):
    """
    Test that every url in docs.html is functional
    """
    settings.API_DOCS_CASE_ID = case.id

    response = client.get('/')
    html = response.content.decode()
    tmp_html = re.sub(";", "", html)
    possible_lines = tmp_html.split("&#39")
    for line in possible_lines:
        if line[0:4] == "http":
            response = client.get(line)
            request_format = "json" if "format=json" in line else None
            check_response(response, format=request_format)



