import pytest
import json


@pytest.mark.django_db
def x_test_get_detail_data(client, jurisdiction):
    response = client.get('/data/details/%s' % jurisdiction.slug)
    result = json.loads(response.content.decode())
    assert "jurisdiction" in result.keys()
    assert result['jurisdiction']['whitelisted'] == jurisdiction.whitelisted
    assert "case_count" in result.keys()
