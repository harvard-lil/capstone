import pytest
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
def test_ExtractedCitationSerializer(api_request_factory, extracted_citation_factory):
    extractedcitation = extracted_citation_factory()
    request = api_request_factory.get(api_reverse("extractedcitation-list"))
    serializer_context = {'request': Request(request)}

    serialized = serializers.ExtractedCitationSerializer(extractedcitation, context=serializer_context)
    assert 'cite' in serialized.data
    assert serialized.data.get('cite') == extractedcitation.cite
