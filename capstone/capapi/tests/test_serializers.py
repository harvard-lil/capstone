import os

import pytest
from rest_framework.request import Request

from capapi import serializers


@pytest.mark.django_db
def test_CaseSerializerWithCasebody(api_url, api_request_factory, case, three_cases):
    # can get single case data
    url = os.path.join(api_url, "cases")
    request = api_request_factory.get(url)
    serializer_context = {'request': Request(request)}

    serialized = serializers.CaseSerializerWithCasebody(case, context=serializer_context)
    assert 'casebody' in serialized.data.keys()

    # can get multiple cases' data
    serialized = serializers.CaseSerializerWithCasebody(three_cases, many=True, context=serializer_context)
    assert len(serialized.data) == 3
    for case in serialized.data:
        assert 'casebody' in case.keys()
