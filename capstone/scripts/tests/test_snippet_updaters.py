import pytest
import json
from scripts import update_snippets
from capdb.models import Snippet

@pytest.mark.django_db(databases=['capdb'])
def test_map_numbers(case_factory, jurisdiction):
    [case_factory(jurisdiction=jurisdiction) for i in range(3)]
    update_snippets.update_map_numbers()
    snippet = Snippet.objects.get(label="map_numbers")
    parsed = json.loads(snippet.contents)
    assert len(parsed) == 1
    assert parsed[jurisdiction.slug]['case_count'] == 3
    assert parsed[jurisdiction.slug]['volume_count'] == 3
    assert parsed[jurisdiction.slug]['page_count'] == 15

@pytest.mark.django_db(databases=['capdb'])
def test_search_jurisdiction_list(jurisdiction):
    update_snippets.search_jurisdiction_list()
    jurisdictions = Snippet.objects.get(label='search_jurisdiction_list')
    parsed = json.loads(jurisdictions.contents)
    assert parsed[0][1] == jurisdiction.name_long

@pytest.mark.django_db(databases=['capdb'])
def test_search_court_list(court):
    update_snippets.search_court_list()
    courts = Snippet.objects.get(label='search_court_list')
    parsed = json.loads(courts.contents)
    assert parsed[0][1] == '%s: %s' % (court.jurisdiction.name_long, court.name)

@pytest.mark.django_db(databases=['capdb'])
def test_court_abbrev_list(court):
    update_snippets.court_abbrev_list()
    courts = Snippet.objects.get(label='court_abbrev_list')
    parsed = json.loads(courts.contents)
    assert parsed[0][1] == court.name

@pytest.mark.django_db(databases=['capdb'])
def test_search_reporter_list(reporter):
    update_snippets.search_reporter_list()
    reporters = Snippet.objects.get(label='search_reporter_list')
    parsed = json.loads(reporters.contents)
    assert len(parsed) == 1
    assert parsed[0][1] == '%s- %s' % (reporter.short_name, reporter.full_name)
