import pytest

import fabfile
from capdb.models import TrackingToolUser, BookRequest, ProcessStep, Reporter, TrackingToolLog, VolumeMetadata, PageXML
from scripts.helpers import parse_xml, serialize_xml

@pytest.mark.django_db
def test_volume_metadata(ingest_volume_xml):
    assert ingest_volume_xml.metadata.hollis_number == "005457617"
    assert ingest_volume_xml.metadata.rare is False  # boolean conversion

@pytest.mark.django_db
def test_tracking_tool_relationships(ingest_volume_xml):
    assert ingest_volume_xml.metadata.reporter.full_name == "Illinois Appellate Court Reports"
    assert ingest_volume_xml.metadata.tracking_tool_logs.first().pstep.pk == 'Prqu'

@pytest.mark.django_db
def test_volume_xml(ingest_volume_xml):
    assert '<reporter abbreviation="Ill. App." volnumber="23">Illinois Appellate Court Reports</reporter>' in ingest_volume_xml.orig_xml

@pytest.mark.django_db
def test_case_and_page_xml(ingest_volume_xml):
    assert ingest_volume_xml.case_xmls.count() == 1
    assert ingest_volume_xml.page_xmls.count() == 6
    case_xml = ingest_volume_xml.case_xmls.first()
    assert '<name abbreviation="Home Insurance Co. of New York v. Kirk">' in case_xml.orig_xml
    assert case_xml.pages.count() == 6

@pytest.mark.django_db
def test_duplicative_case_xml(ingest_duplicative_case_xml):
    assert ingest_duplicative_case_xml.metadata.duplicative is True
    assert ingest_duplicative_case_xml.metadata.first_page == "1"
    assert ingest_duplicative_case_xml.metadata.last_page == "4"

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

