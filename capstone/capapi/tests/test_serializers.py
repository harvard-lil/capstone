import os

import pytest
from rest_framework.request import Request

from capapi import serializers
from test_data.test_fixtures.factories import setup_case


@pytest.mark.django_db(transaction=True)
def test_CaseSerializerWithCasebody(api_url, api_request_factory, auth_client, case):
    # can get single case data
    url = os.path.join(api_url, "cases")
    request = api_request_factory.get(url)
    serializer_context = {'request': Request(request)}

    serialized = serializers.CaseSerializerWithCasebody(case, context=serializer_context)
    assert serialized.data['slug'] == case.slug
    assert 'casebody' in serialized.data.keys()

    # can get multiple cases' data
    cases = []
    for c in range(0, 3):
        case = setup_case()
        cases.append(case)

    serialized = serializers.CaseSerializerWithCasebody(cases, many=True, context=serializer_context)
    assert len(serialized.data) == 3
    for case in serialized.data:
        assert 'casebody' in case.keys()
