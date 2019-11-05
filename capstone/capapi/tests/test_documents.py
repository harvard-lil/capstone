import pytest
from capdb.models import CaseMetadata


@pytest.mark.django_db
def test_case_document_get_frontend_url(client, case_document, ingest_metadata):
    case = CaseMetadata.objects.get(name=case_document.name)
    assert case.get_frontend_url() == case_document.get_frontend_url()

@pytest.mark.django_db
def test_case_document_full_cite(client, case_document, ingest_metadata):
    case = CaseMetadata.objects.get(name=case_document.name)
    assert case.full_cite() == case_document.full_cite()
