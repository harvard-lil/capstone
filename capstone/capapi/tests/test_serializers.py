import pytest
from rest_framework.request import Request

from capapi import serializers
from capapi.resources import api_reverse


#@pytest.mark.django_db
@pytest.mark.skip
def test_CaseSerializerWithCasebody(api_request_factory, es_whitelisted_case, es_three_cases):
    # can get single case data
    request = api_request_factory.get(api_reverse("cases-list"))
    serializer_context = {'request': Request(request)}

    serialized = serializers.CaseSerializerWithCasebody(es_whitelisted_case, context=serializer_context)
    assert 'casebody' in serialized.data.keys()

    # can get multiple cases' data
    serialized = serializers.CaseSerializerWithCasebody(es_three_cases, many=True, context=serializer_context)
    assert len(serialized.data) == 3
    for case in serialized.data:
        assert 'casebody' in case.keys()
