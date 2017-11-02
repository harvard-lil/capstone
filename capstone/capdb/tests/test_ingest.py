import pytest

import fabfile
from capdb.models import TrackingToolUser, BookRequest, ProcessStep, Reporter, TrackingToolLog, VolumeMetadata


@pytest.mark.django_db
def test_volume_metadata(volume_xml):
    assert volume_xml.volume_metadata.hollis_number == "005457617"
    assert volume_xml.volume_metadata.rare is False  # boolean conversion

@pytest.mark.django_db
def test_tracking_tool_relationship(volume_xml):
    assert volume_xml.volume_metadata.reporter.full_name == "Illinois Appellate Court Reports"

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
def test_update_dup_checking(volume_xml):
    fabfile.total_sync_with_s3()
    test_case_and_page_xml(volume_xml)

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