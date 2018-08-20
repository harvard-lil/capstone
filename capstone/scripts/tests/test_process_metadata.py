import os
import pytest
import datetime
from scripts.helpers import read_file
from scripts import process_metadata


@pytest.mark.django_db
def test_get_single_case_metadata(ingest_case_xml):
    case = process_metadata.get_case_metadata(ingest_case_xml.orig_xml)

    assert case['duplicative'] is False

    assert type(case["parties"]) is list
    parties = case["parties"]
    assert "John Kirk" in parties[0]

    assert type(case['decision_date']) is datetime.date
    assert type(case['decision_date_original']) is str

    assert case['jurisdiction'] == 'Illinois'

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
                    assert type(case_metadata["decision_date"]) is datetime.date
                    assert type(case_metadata["decision_date_original"]) is str
                    assert type(case_metadata["opinions"]) is list
                    assert type(case_metadata["attorneys"]) is list
                    assert type(case_metadata["judges"]) is list
                    assert type(case_metadata["parties"]) is list

def test_case_metadata_opinion():
    # test case with no opinion author
    casemets_file = "test_data/from_vendor/32044057891608_redacted/casemets/32044057891608_redacted_CASEMETS_0001.xml"
    case_xml = read_file(casemets_file)
    case_metadata = dict(process_metadata.get_case_metadata(case_xml))
    assert type(case_metadata["parties"]) is list
    assert case_metadata["opinions"][0] == {"type": "majority", "author": None}

    # test case with opinion author
    casemets_file = "test_data/from_vendor/32044057892259_redacted/casemets/32044057892259_redacted_CASEMETS_0001.xml"
    case_xml = read_file(casemets_file)
    case_metadata = dict(process_metadata.get_case_metadata(case_xml))
    assert case_metadata["opinions"][0] == {"type": "majority", "author": "Lacey, J."}

