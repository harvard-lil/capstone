import pytest
import datetime

from scripts.process_metadata import get_case_metadata


@pytest.mark.django_db
def test_get_metadata(ingest_case_xml):
    case = get_case_metadata(ingest_case_xml.orig_xml)

    assert case['duplicative'] is False

    assert type(case["parties"]) is str
    parties = case["parties"]
    assert "John Kirk" in parties

    assert type(case['decision_date']) is datetime.datetime
    assert type(case['decision_date_original']) is str

    assert case['jurisdiction'] == 'Illinois'
