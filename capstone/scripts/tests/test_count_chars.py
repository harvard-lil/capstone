import pytest
import json
from scripts import count_chars
from os import walk, rmdir, remove
from os.path import isdir

@pytest.mark.django_db
def test_counts_as_written_to_files(ingest_case_xml):
    path="/tmp/count_test"

    count_chars.count_chars_in_all_cases(path)

    for directory, subdirs, files in walk(path):
        for i in files:
            filepath = "{}/{}".format(path, i)
            remove(filepath)
    rmdir(path)

    assert not isdir(path)

    count_chars.count_chars_in_all_cases(path)

    for directory, subdirs, files in walk(path):
        assert len(files) == 3
        for i in files:
            filepath = "{}/{}".format(path, i)
            json_file_handle = open(filepath, mode="r")
            output = json.load(json_file_handle)
            json_file_handle.close()
            assert output['whole_xml_counts'] != {}
            assert output['whole_xml_counts']['<'] > 0
            assert output['whole_xml_counts']['<'] == output['whole_xml_counts']['>']
            if output['metadata']['duplicative']:
                assert output['casebody_text_no_soft_hyphen_counts'] == {}
            else:
                assert output['casebody_text_no_soft_hyphen_counts'] != {}
            remove(filepath)
    rmdir(path)