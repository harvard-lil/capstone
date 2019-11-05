import pytest
from capdb.models import CaseMetadata


@pytest.mark.django_db
def test_case_document_get_frontend_url(client, whitelisted_case_document, ingest_metadata):
    case = CaseMetadata.objects.get(name=whitelisted_case_document.name)
    assert case.get_frontend_url() == whitelisted_case_document.get_frontend_url()

@pytest.mark.django_db
def test_case_document_full_cite(client, whitelisted_case_document, ingest_metadata):
    case = CaseMetadata.objects.get(name=whitelisted_case_document.name)
    assert case.full_cite() == whitelisted_case_document.full_cite()
