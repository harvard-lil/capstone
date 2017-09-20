import os
import datetime

from scripts import process_metadata
from scripts.helpers import read_file


def test_get_case_metadata():
    casemets_test_dir = "test_data/from_vendor"
    for root, dirs, files in os.walk(casemets_test_dir):
        for fname in files:
            if "_redacted_CASEMETS" in fname:
                case_xml = read_file("%s/%s" % (root, fname))
                case_metadata = process_metadata.get_case_metadata(case_xml)
                assert len(case_metadata["name"]) > 0
                assert len(case_metadata["jurisdiction"]) > 0
                assert len(case_metadata["volume_barcode"]) > 0
                assert type(case_metadata["decision_date"]) is datetime.datetime
                assert type(case_metadata["decision_date_original"]) is str

