import pytest

import scripts.edits.tribal_jurisdiction


@pytest.mark.django_db
def test_tribal_jurisdiction(ingest_case_xml):
    # set up conditions for edit
    case = ingest_case_xml.metadata
    case.jurisdiction.name_long = "United States"
    case.jurisdiction.save()
    case.reporter.full_name = "West's American Tribal Law Reporter"
    case.reporter.save()

    # dry run
    original_jurisdiction = case.jurisdiction
    scripts.edits.tribal_jurisdiction.make_edits()
    case.refresh_from_db()
    assert case.jurisdiction == original_jurisdiction

    # real run
    scripts.edits.tribal_jurisdiction.make_edits(dry_run=False)
    case.refresh_from_db()
    assert case.jurisdiction != original_jurisdiction
    assert case.jurisdiction.name == "Tribal"
