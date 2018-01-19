import os
import datetime
import pytest

from capdb.models import CaseMetadata
from capdb.tasks import create_case_metadata_from_all_vols
from scripts import process_metadata
from scripts.helpers import read_file


def test_get_case_metadata():
    casemets_test_dir = "test_data/from_vendor"
    for root, dirs, files in os.walk(casemets_test_dir):
        for fname in files:
            if "_redacted_CASEMETS" in fname:
                case_xml = read_file("%s/%s" % (root, fname))
                case_metadata = process_metadata.get_case_metadata(case_xml)
                assert len(case_metadata["volume_barcode"]) > 0

                if not case_metadata['duplicative']:
                    assert len(case_metadata["name"]) > 0
                    assert len(case_metadata["jurisdiction"]) > 0
                    assert type(case_metadata["decision_date"]) is datetime.datetime
                    assert type(case_metadata["decision_date_original"]) is str
                    assert type(case_metadata["opinions"]) is str
                    assert type(case_metadata["attorneys"]) is str
                    assert type(case_metadata["judges"]) is str
                    assert type(case_metadata["opinions"]) is str
                    assert type(case_metadata["parties"]) is str


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