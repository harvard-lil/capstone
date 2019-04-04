import pytest

from capdb.models import Court
from scripts.edits import merge_courts


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
