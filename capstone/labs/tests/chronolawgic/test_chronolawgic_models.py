import pytest
from labs.models import Timeline

cases = [
    {'id': 'asdsa', 'url': 'https://cite.case.law/ill/1/176/', 'name': 'Case 2', 'citation': '1 Mass. 1',
     'reporter': "Abb. Pr.- Abbott's Practice Reports", 'jurisdiction': 'California',
     'decision_date': '1898-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'},
    {'id': 'asdsadsadsa', 'url': 'http://cite.case.test:8000/ill-app-2d/59/188/', 'name': 'Gurshey v. Chicago Transit Authority',
     'citation': '59 Ill. App. 2d 188', 'reporter': '', 'categories': [], 'jurisdiction': '',
     'decision_date': '1965-05-10', 'long_description': '', 'short_description': ''},
    {'id': 'faijfijsai', 'url': 'http://cite.case.test:8000/ill/146/64/', 'name': 'City of Chicago v. Brownell',
     'citation': '146 Ill. 64', 'reporter': '', 'categories': [], 'jurisdiction': '', 'decision_date': '1893-06-19',
     'long_description': '', 'short_description': ''}
]
events = [
    {'id': 'askjdsijda-dsa-d-sa-dsa-dsa-', 'name': 'Event 6', 'color': '#00db67', 'end_date': '1878-12-31', 'start_date': '1875-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'},
    {'id': 'da-dadada-da-d-a-23-2-d-a-da', 'name': 'Event 6', 'color': '#00B7DB', 'end_date': '1877-12-31', 'start_date': '1875-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'}
]
timeline_data = {"title": "My first timeline", "description": "And my very best one", "cases": cases, "events": events}


@pytest.mark.django_db(databases=['default'])
def test_uuid_workflow(cap_user):
    timeline1 = Timeline(timeline=timeline_data, created_by=cap_user)
    timeline1.save()

    assert Timeline.objects.count() == 1

    timeline2 = Timeline(timeline=timeline_data, created_by=cap_user)
    timeline2.uuid = timeline1.uuid
    timeline2.save()
    timeline2.refresh_from_db()

    assert Timeline.objects.count() == 2
    assert timeline2.uuid != timeline1.uuid


def test_stats(cap_user):
    first_year = 1875
    last_year = 1965
    case_years = [1893, 1898, 1965]
    event_years = [1875, 1876, 1877, 1878]
    case_stats = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    event_stats = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    timeline = Timeline(timeline=Timeline.generate_empty_timeline(timeline_data), created_by=cap_user)
    timeline.save()

    generated_case_years = timeline.case_years()
    generated_event_years = timeline.event_years()
    generated_first_year = Timeline.first_year(generated_case_years, generated_event_years)
    generated_last_year = Timeline.last_year(generated_case_years, generated_event_years)
    generated_case_stats = Timeline.case_stats(generated_case_years, generated_first_year, generated_last_year)
    generated_event_stats = Timeline.event_stats(generated_event_years, generated_first_year, generated_last_year)

    assert case_stats == generated_case_stats
    assert event_stats == generated_event_stats
    assert case_years == generated_case_years
    assert event_years == generated_event_years

    assert generated_first_year == first_year
    assert generated_last_year == last_year

