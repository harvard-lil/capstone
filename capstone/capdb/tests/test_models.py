import pytest

from capdb.models import CaseMetadata
from scripts.helpers import parse_xml, serialize_xml

@pytest.mark.django_db
def test_case_alto_update_tag(case_xml):

    updated_case = parse_xml(case_xml.orig_xml)
    updated_case('casebody|p[id="b17-6"]').text("The 4rgUm3nt in favor of the appellee rests wholly on the assumption that the judgment in the garnishee proceedings should be rendered in favor of the judgment debtor for the use of the judgment creditor, against the garnished party, for the whole amount due, and in case of failure to so render judgment for such amount and for a less amount than due, the balance over and above the amount of the judgment so rendered would be barred on the grounds of former recovery.")
    print(case_xml.update_case(updated_case))


@pytest.mark.django_db
def test_update_case_metadata(case_xml):
    # fetch current metadata
    case_metadata = CaseMetadata.objects.get(case_id=case_xml.case_id)

    # change xml
    parsed = parse_xml(case_xml.orig_xml)
    parsed('case|citation[category="official"]').text('123 Test 456')
    case_xml.orig_xml = serialize_xml(parsed)
    case_xml.save()
    case_xml.update_case_metadata()

    # fetch new metadata
    new_case_metadata = CaseMetadata.objects.get(case_id=case_xml.case_id)
    new_citations = list(new_case_metadata.citations.all())

    # case_metadata should have been updated, not duplicated
    assert new_case_metadata.pk == case_metadata.pk
    assert new_case_metadata.slug == '123-test-456'

    # citations should have been replaced
    assert len(new_citations) == 1
    assert new_citations[0].cite == '123 Test 456'
