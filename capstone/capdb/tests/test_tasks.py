import pytest
import bagit
import zipfile

from capdb.models import CaseMetadata
from capdb.tasks import create_case_metadata_from_all_vols
import fabfile

@pytest.mark.django_db
def test_create_case_metadata_from_all_vols(ingest_case_xml):
    # get initial state
    metadata_count = CaseMetadata.objects.count()
    case_id = ingest_case_xml.metadata.case_id

    # delete case metadata
    ingest_case_xml.metadata.delete()
    assert CaseMetadata.objects.count() == metadata_count - 1

    # recreate case metadata
    create_case_metadata_from_all_vols()

    # check success
    ingest_case_xml.refresh_from_db()
    assert CaseMetadata.objects.count() == metadata_count
    assert ingest_case_xml.metadata.case_id == case_id

@pytest.mark.django_db
def test_zip_jurisdiction(case_xml, tmpdir):
    # get the jurisdiction of the ingested case
    jurisdiction = case_xml.metadata.jurisdiction
    # zip the jurisdiction
    zip_path = str(tmpdir / jurisdiction.name) + '.zip'
    fabfile.zip_jurisdiction(jurisdiction.name, zip_filename=zip_path)
    # unzip the resulting file -- can we get the filename from the object?
    with zipfile.ZipFile(zip_path) as zf:
        zipped_xml = zf.read("%s/%d/%s" % (
            case_xml.metadata.reporter.short_name,
            case_xml.volume.metadata.volume_number,
            "32044057892259_0001.xml")
        )
    assert zipped_xml == bytes(case_xml.orig_xml, encoding='utf-8')

@pytest.mark.django_db
def test_bag_jurisdiction(case_xml, tmpdir):
    # get the jurisdiction of the ingested case
    jurisdiction = case_xml.metadata.jurisdiction
    # bag the jurisdiction
    fabfile.bag_jurisdiction(jurisdiction.name, zip_directory=tmpdir)
    # validate the bag
    bag_path = str(tmpdir / jurisdiction.slug)
    with zipfile.ZipFile(bag_path + '.zip') as zf:
        zf.extractall(str(tmpdir))
    bag = bagit.Bag(bag_path)
    assert bag.is_valid()
