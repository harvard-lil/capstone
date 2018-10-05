import pytest
from rest_framework.request import Request

from capapi import serializers
from capapi.resources import api_reverse


@pytest.mark.django_db
def test_CaseSerializerWithCasebody(api_request_factory, case, three_cases):
    # can get single case data
    request = api_request_factory.get(api_reverse("casemetadata-list"))
    serializer_context = {'request': Request(request)}

    serialized = serializers.CaseSerializerWithCasebody(case, context=serializer_context)
    assert 'casebody' in serialized.data.keys()

    # can get multiple cases' data
    serialized = serializers.CaseSerializerWithCasebody(three_cases, many=True, context=serializer_context)
    assert len(serialized.data) == 3
    for case in serialized.data:
        assert 'casebody' in case.keys()
