import pytest

from capdb.models import Court
from scripts.edits import tribal_jurisdiction, strip_court_names, merge_courts


@pytest.mark.django_db
def test_tribal_jurisdiction(ingest_case_xml):
    # set up conditions for edit
    case = ingest_case_xml.metadata
    case.jurisdiction.name_long = "United States"
    case.jurisdiction.save()
    case.reporter.full_name = "West's American Tribal Law Reporter"
    case.reporter.save()
    original_jurisdiction = case.jurisdiction

    # dry run
    tribal_jurisdiction.make_edits()
    case.refresh_from_db()
    assert case.jurisdiction == original_jurisdiction

    # real run
    tribal_jurisdiction.make_edits(dry_run=False)
    case.refresh_from_db()
    assert case.jurisdiction != original_jurisdiction
    assert case.jurisdiction.name == "Tribal"


@pytest.mark.django_db
def test_strip_court_names(ingest_case_xml):
    case_xml = ingest_case_xml
    case = case_xml.metadata
    right_court = case.court
    wrong_court_name = right_court.name+'`'
    wrong_court_abbrev = right_court.name_abbreviation+'`'
    case_xml.orig_xml = case_xml.orig_xml.replace(right_court.name_abbreviation, wrong_court_abbrev).replace(right_court.name, wrong_court_name)
    case_xml.save()
    case.refresh_from_db()
    wrong_court = case.court
    assert wrong_court != right_court
    assert wrong_court.name == wrong_court_name

    # dry run
    strip_court_names.make_edits()
    case.refresh_from_db()
    assert case.court == wrong_court

    # real run
    strip_court_names.make_edits(dry_run=False)
    case.refresh_from_db()
    assert case.court == right_court

@pytest.mark.django_db
def test_merge_courts(case, court):
    wrong_court = Court(name=court.name, name_abbreviation=court.name_abbreviation, jurisdiction_id=court.jurisdiction_id, slug=court.slug+'-1')
    wrong_court.save()
    case.court = wrong_court
    case.save()

    # dry run
    merge_courts.make_edits()
    case.refresh_from_db()
    assert case.court == wrong_court

    # real run
    merge_courts.make_edits(dry_run=False)
    case.refresh_from_db()
    assert case.court == court
