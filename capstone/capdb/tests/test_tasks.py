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
def test_bag_jurisdiction(ingest_case_xml, tmpdir):
    # get the jurisdiction of the ingested case
    jurisdiction = ingest_case_xml.metadata.jurisdiction
    # bag the jurisdiction
    fabfile.bag_jurisdiction(jurisdiction.name, zip_directory=tmpdir)
    # validate the bag
    bag_path = str(tmpdir / jurisdiction.slug)
    with zipfile.ZipFile(bag_path + '.zip') as zf:
        zf.extractall(str(tmpdir))
    bag = bagit.Bag(bag_path)
    assert bag.is_valid()
