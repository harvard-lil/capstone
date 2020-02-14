import pytest

import fabfile
from capdb.models import VolumeMetadata, PageXML, CaseXML
from scripts.helpers import parse_xml, serialize_xml

@pytest.mark.django_db
def test_ingested_xml(ingest_volume_xml):
    # volume xml ingest
    assert '<reporter abbreviation="Ill. App." volnumber="23">Illinois Appellate Court Reports</reporter>' in ingest_volume_xml.orig_xml

    # volume metadata
    assert ingest_volume_xml.metadata.hollis_number == "005457617"
    assert ingest_volume_xml.metadata.rare is False  # boolean conversion

    # case and page relationships
    assert ingest_volume_xml.case_xmls.count() == 1
    assert ingest_volume_xml.page_xmls.count() == 6
    case_xml = ingest_volume_xml.case_xmls.first()
    assert '<name abbreviation="Home Insurance Co. of New York v. Kirk">' in case_xml.orig_xml
    assert case_xml.pages.count() == 6

    # new style barcode
    new_style_vol = VolumeMetadata.objects.get(pk="WnApp_199")
    assert new_style_vol.rare is False
    assert new_style_vol.reporter.full_name == 'Washington Appellate Reports'
    assert new_style_vol.volume_xml.page_xmls.count() == 6
    assert new_style_vol.volume_xml.case_xmls.count() == 1

    # duplicative case
    ingest_duplicative_case_xml = CaseXML.objects.get(metadata__case_id='32044061407086_0001')
    assert ingest_duplicative_case_xml.metadata.duplicative is True
    assert ingest_duplicative_case_xml.metadata.first_page == "1"
    assert ingest_duplicative_case_xml.metadata.last_page == "4"

@pytest.mark.skip(reason="Currently this intentionally fails -- total_sync_with_s3 does not import volumes"
                         "that are already imported, so we don't overwrite database changes.")
@pytest.mark.django_db
def test_update_dup_checking(ingest_volume_xml, ingest_case_xml):

    # get ALTO
    page_xml = PageXML.objects.get(barcode='32044057892259_00008_0')

    # Make sure we've go the right text
    assert 'Insurance' in ingest_case_xml.orig_xml
    assert 'Insurance' in page_xml.orig_xml

    # change corresponding value in casemets
    parsed_case = parse_xml(ingest_case_xml.orig_xml)
    parsed_case('casebody|parties[id="b15-4"]').text('The Home Inversion Company of New York v. John Kirk, for use of William Kirk.')
    ingest_case_xml.orig_xml = serialize_xml(parsed_case)
    ingest_case_xml.save()

    ingest_volume_xml.refresh_from_db()
    ingest_case_xml.refresh_from_db()
    page_xml.refresh_from_db()

    # make sure the writes worked. If they failed, the test would falsely pass
    assert 'Inversion' in ingest_case_xml.orig_xml
    assert 'Inversion' in page_xml.orig_xml

    fabfile.total_sync_with_s3()

    ingest_volume_xml.refresh_from_db()
    ingest_case_xml.refresh_from_db()
    page_xml.refresh_from_db()

    assert 'Inversion' not in ingest_case_xml.orig_xml
    assert 'Inversion' not in page_xml.orig_xml
