import pytest
import re
from rest_framework.request import Request

from capapi import serializers
from capapi.documents import CaseDocument
from capapi.resources import api_reverse


@pytest.mark.django_db
def test_CaseDocumentSerializerWithCasebody(api_request_factory, case_factory, elasticsearch):
    cases = [case_factory() for i in range(3)]
    case_documents = [CaseDocument.get(c.id) for c in cases]

    # can get single case data
    request = api_request_factory.get(api_reverse("cases-list"))
    request.accepted_renderer = None
    serializer_context = {'request': Request(request)}

    serialized = serializers.CaseDocumentSerializerWithCasebody(case_documents[0], context=serializer_context)
    assert 'casebody' in serialized.data

    # can get multiple cases' data
    serialized = serializers.CaseDocumentSerializerWithCasebody(case_documents, many=True, context=serializer_context)
    assert len(serialized.data) == 3
    for case in serialized.data:
        assert 'casebody' in case


@pytest.mark.django_db
def test_CitationSerializer(api_request_factory, case_metadata):
    request = api_request_factory.get(api_reverse("citation-list"))
    serializer_context = {'request': Request(request)}

    serialized = serializers.CitationWithCaseSerializer(case_metadata.citations.first(), context=serializer_context)

    url_pattern = api_reverse("cases-list") + str(case_metadata.pk) + '/'
    assert re.match(url_pattern, serialized.data['case_url'])

    assert case_metadata.citations.first().type == serialized.data['type']
    assert case_metadata.citations.first().cite == serialized.data['cite']
    assert 'normalized_cite' not in serialized.data
