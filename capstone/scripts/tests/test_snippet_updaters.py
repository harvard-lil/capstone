import pytest
import json
from scripts import update_snippets
from capdb.models import Snippet

@pytest.mark.django_db
def test_map_numbers(case_factory, jurisdiction_factory):
    jurisdiction = jurisdiction_factory(slug='ill')
    [case_factory(jurisdiction=jurisdiction) for i in range(3)]
    update_snippets.update_map_numbers()
    snippet = Snippet.objects.get(label="map_numbers")
    parsed = json.loads(snippet.contents)
    assert len(parsed) == 1
    assert parsed['US-IL']['case_count'] == 3
    assert parsed['US-IL']['volume_count'] == 3
    assert parsed['US-IL']['page_count'] == 15

@pytest.mark.django_db
def test_cases_by_decision_date(case_factory):
    cases = [case_factory() for i in range(3)]
    update_snippets.cases_by_decision_date_tsv()
    cases_by_decision_date = Snippet.objects.get(label='cases_by_decision_date')
    for case in cases:
        assert case.decision_date_original in cases_by_decision_date.contents

@pytest.mark.django_db
def test_cases_by_jurisdiction(jurisdiction, case_factory):
    [case_factory(jurisdiction=jurisdiction) for i in range(3)]
    update_snippets.cases_by_jurisdiction_tsv()
    cases_by_jurisdiction = Snippet.objects.get(label='cases_by_jurisdiction')
    rows = cases_by_jurisdiction.contents.split("\r\n")[:-1]
    assert len(rows) == 1
    assert rows[0].split("\t")[1] == '"%s"' % jurisdiction.name_long
    assert rows[0].split("\t")[2] == '3'

@pytest.mark.django_db
def test_cases_by_reporter(reporter, case_factory):
    [case_factory(reporter=reporter) for i in range(3)]
    update_snippets.cases_by_reporter_tsv()
    cases_by_reporter = Snippet.objects.get(label='cases_by_reporter')
    rows = cases_by_reporter.contents.split("\r\n")[:-1]
    assert len(rows) == 1
    assert rows[0].split("\t")[1] == '"%s"' % reporter.full_name
    assert rows[0].split("\t")[2] == '3'

@pytest.mark.django_db
def test_search_jurisdiction_list(jurisdiction):
    update_snippets.search_jurisdiction_list()
    jurisdictions = Snippet.objects.get(label='search_jurisdiction_list')
    parsed = json.loads(jurisdictions.contents)
    assert parsed[0][1] == jurisdiction.name_long

@pytest.mark.django_db
def test_search_court_list(court):
    update_snippets.search_court_list()
    courts = Snippet.objects.get(label='search_court_list')
    parsed = json.loads(courts.contents)
    assert parsed[0][1] == '%s: %s' % (court.jurisdiction.name_long, court.name)

@pytest.mark.django_db
def test_search_reporter_list(reporter):
    update_snippets.search_reporter_list()
    reporters = Snippet.objects.get(label='search_reporter_list')
    parsed = json.loads(reporters.contents)
    assert len(parsed) == 1
    assert parsed[0][1] == '%s- %s' % (reporter.short_name, reporter.full_name)
