import pytest

import fabfile
from capdb.models import TrackingToolUser, BookRequest, ProcessStep, Reporter, TrackingToolLog, VolumeMetadata, PageXML
from scripts.helpers import parse_xml, serialize_xml

@pytest.mark.django_db
def test_volume_metadata(volume_xml):
    assert volume_xml.metadata.hollis_number == "005457617"
    assert volume_xml.metadata.rare is False  # boolean conversion

@pytest.mark.django_db
def test_tracking_tool_relationships(volume_xml):
    assert volume_xml.metadata.reporter.full_name == "Illinois Appellate Court Reports"
    assert volume_xml.metadata.tracking_tool_logs.first().pstep.pk == 'Prqu'

@pytest.mark.django_db
def test_volume_xml(volume_xml):
    assert '<reporter abbreviation="Ill. App." volnumber="23">Illinois Appellate Court Reports</reporter>' in volume_xml.orig_xml

@pytest.mark.django_db
def test_case_and_page_xml(volume_xml):
    assert volume_xml.case_xmls.count() == 1
    assert volume_xml.page_xmls.count() == 6
    case_xml = volume_xml.case_xmls.first()
    assert '<name abbreviation="Home Insurance Co. of New York v. Kirk">' in case_xml.orig_xml
    assert case_xml.pages.count() == 6

@pytest.mark.django_db
def test_duplicative_case_xml(duplicative_case_xml):
    assert duplicative_case_xml.metadata.duplicative is True
    assert duplicative_case_xml.metadata.first_page == "1"
    assert duplicative_case_xml.metadata.last_page == "4"

@pytest.mark.django_db
def test_update_dup_checking(volume_xml, case_xml):
    def test_update_dup_checking(ingest_volume_xml, ingest_case_xml):
        fabfile.total_sync_with_s3()

        # change value in ALTO
        page_xml = PageXML.objects.get(barcode='32044057892259_00008_0')
        original_page_md5 = page_xml.md5
        parsed_page = parse_xml(page_xml.orig_xml)
        parsed_page('alto|String[ID="ST_15.2.1.5"]').attr["CONTENT"] = "Inversion"
        page_xml.orig_xml = str(parsed_page)
        page_xml.save()

        # change corresponding value in casemets
        parsed_case = parse_xml(ingest_case_xml.orig_xml)
        original_case_md5 = ingest_case_xml.md5
        parsed_case('casebody|parties[id="b15-4"]').text(
            'The Home Inversion Company of New York v. John Kirk, for use of William Kirk.')
        parsed_case('mets|file[ID="alto_00008_0"]').attr["CHECKSUM"] = page_xml.md5
        ingest_case_xml.orig_xml = str(parsed_case)
        ingest_case_xml.save()

        # update checksums in volume mets
        parsed_volume = parse_xml(ingest_volume_xml.orig_xml)
        parsed_volume('mets|file[ID="alto_00008_0"]').attr["CHECKSUM"] = page_xml.md5
        parsed_volume('mets|file[ID="casemets_0001"]').attr["CHECKSUM"] = ingest_case_xml.md5
        ingest_volume_xml.save()

        # make sure the writes worked. If they failed, the test would falsely pass
        assert original_page_md5 != page_xml.md5
        assert original_case_md5 != ingest_case_xml.md5
        assert 'Inversion' in ingest_case_xml.orig_xml
        assert 'Inversion' in page_xml.orig_xml

        fabfile.total_sync_with_s3()

        ingest_volume_xml.refresh_from_db()
        ingest_case_xml.refresh_from_db()
        page_xml.refresh_from_db()

        assert original_page_md5 == page_xml.md5
        assert original_case_md5 == ingest_case_xml.md5
        assert 'Inversion' not in ingest_case_xml.orig_xml
        assert 'Inversion' not in page_xml.orig_xml


@pytest.mark.django_db
def test_sync_metadata(ingest_metadata):
    # helper to get count of all migrated models
    models = [VolumeMetadata, TrackingToolLog, Reporter, ProcessStep, BookRequest, TrackingToolUser]
    def get_counts():
        return {Model: Model.objects.count() for Model in models}

    # get count for each model following initial ingest_metadata() fixture
    orig_counts = get_counts()

    # make sure they all loaded
    for Model, count in orig_counts.items():
        assert count > 0, "%s did not load any items during ingest_metadata" % Model

    # delete a couple of objects
    for Model in [TrackingToolLog, BookRequest]:
        Model.objects.first().delete()

    # sync metadata
    fabfile.sync_metadata()

    # make sure deleted objects were restored
    new_counts = get_counts()
    assert new_counts == orig_counts