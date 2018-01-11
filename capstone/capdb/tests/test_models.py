import pytest

from capdb.models import CaseMetadata
from scripts.helpers import parse_xml, serialize_xml
from test_data.test_fixtures.factories import *

### BaseXMLModel ###

@pytest.mark.django_db
def test_database_should_not_modify_xml(volume_xml, unaltered_alto_xml):
    # make sure that XMLField.from_db_value is doing its job and putting the correct XML declaration back in:
    volume_xml.orig_xml = unaltered_alto_xml
    volume_xml.save()
    volume_xml.refresh_from_db()
    assert volume_xml.orig_xml == unaltered_alto_xml.decode()
    assert volume_xml.md5 == volume_xml.get_md5()


### CaseMetadata ###

@pytest.mark.django_db
def test_create_or_update_metadata(ingest_case_xml):
    # fetch current metadata
    case_metadata = ingest_case_xml.metadata

    # change xml
    parsed = parse_xml(ingest_case_xml.orig_xml)
    parsed('case|citation[category="official"]').text('123 Test 456')
    ingest_case_xml.orig_xml = serialize_xml(parsed)
    ingest_case_xml.save()
    ingest_case_xml.create_or_update_metadata()

    # fetch new metadata
    new_case_metadata = CaseMetadata.objects.get(pk=case_metadata.pk)
    new_citations = list(new_case_metadata.citations.all())

    # case_metadata should have been updated, not duplicated
    assert new_case_metadata.pk == case_metadata.pk
    assert new_case_metadata.slug == '123-test-456'

    # citations should have been replaced
    assert len(new_citations) == 1
    assert new_citations[0].cite == '123 Test 456'

    # testing calling without updating metadata
    old_case_metadata = new_case_metadata
    ingest_case_xml.orig_xml = "Nothing to see here"
    ingest_case_xml.save()
    ingest_case_xml.refresh_from_db()
    ingest_case_xml.create_or_update_metadata(update_existing=False)
    new_case_metadata = CaseMetadata.objects.get(pk=case_metadata.pk)
    assert new_case_metadata == old_case_metadata

@pytest.mark.django_db
def test_related_names():
    jur = setup_jurisdiction()
    rep = setup_reporter()
    court = setup_court()
    vol = setup_volume()

    case = setup_case(**{
        'jurisdiction': jur,
        'reporter': rep,
        'court': court,
        'volume': vol,
    })

    assert case in jur.case_metadatas.all()
    assert case in rep.case_metadatas.all()
    assert case in court.case_metadatas.all()
    assert case in vol.case_metadatas.all()

    volxml = setup_volumexml()
    casexml = setup_casexml(**{'volume': volxml})

    casexml.create_or_update_metadata(case)
    assert casexml in volxml.case_xmls.all()
