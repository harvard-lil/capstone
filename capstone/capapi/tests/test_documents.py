import pytest
from capdb.models import CaseMetadata


@pytest.mark.django_db
def test_case_document_full_cite(client, whitelisted_case_document, ingest_django_fixtures):
    case = CaseMetadata.objects.get(name=whitelisted_case_document.name)
    assert case.full_cite() == whitelisted_case_document.full_cite()
