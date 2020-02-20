import os
import datetime

from scripts.fix_court_tag.fix_court_tag import fix_court_tag
from scripts.helpers import read_file
from scripts import process_metadata


def test_fix_court_tag():
    to_check = (
        # manual_fixes.csv:
        # works with hand-coded replacement values
        (('Alabama', ' Alabama  Court of Criminal  Appeal ', ' Ala.  Crim.  App. '), ('Alabama', 'Alabama Court of Criminal Appeals', 'Ala. Crim. App.')),
        # works with ID-based replacement values
        (('Alabama', 'Alaska Court of Appeals', 'Alaska Ct. App.'), ('Alaska', 'Alaska Court of Appeals', 'Alaska Ct. App.')),
        # tribal_jurisdictions.csv:
        (('United States', 'Appellate Court of the Hopi Tribe', 'Hopi Tribe Ct. App.'), ('Tribal Jurisdictions', 'Appellate Court of the Hopi Tribe', 'Hopi Tribe Ct. App.')),
    )
    for old_info, new_info in to_check:
        assert fix_court_tag(*old_info) == new_info

def test_get_case_metadata():
    casemets_test_dir = "test_data/from_vendor"
    for root, dirs, files in os.walk(casemets_test_dir):
        for fname in files:
            if "_redacted_CASEMETS" in fname:
                case_xml = read_file("%s/%s" % (root, fname))
                case_metadata, parsed = process_metadata.get_case_metadata(case_xml)
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
    case_metadata, parsed = process_metadata.get_case_metadata(case_xml)
    assert type(case_metadata["parties"]) is list
    assert case_metadata["opinions"][0] == {"type": "majority", "author": None}

    # test case with opinion author
    casemets_file = "test_data/from_vendor/32044057892259_redacted/casemets/32044057892259_redacted_CASEMETS_0001.xml"
    case_xml = read_file(casemets_file)
    case_metadata, parsed = process_metadata.get_case_metadata(case_xml)
    assert case_metadata["opinions"][0] == {"type": "majority", "author": "Lacey, J."}

