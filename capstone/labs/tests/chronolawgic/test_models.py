import pytest
from labs.models import Timeline

cases = [
    {'id': 1, 'url': 'https://cite.case.law/ill/1/176/', 'name': 'Case 2', 'citation': '1 Mass. 1', 'created_by': 1,
     'reporter': "Abb. Pr.- Abbott's Practice Reports", 'jurisdiction': 'California',
     'decision_date': '1898-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'},
    {'id': 5, 'url': 'http://cite.case.test:8000/ill-app-2d/59/188/', 'name': 'Gurshey v. Chicago Transit Authority',
     'citation': '59 Ill. App. 2d 188', 'reporter': '', 'categories': [], 'jurisdiction': '',
     'decision_date': '1965-05-10', 'long_description': '', 'short_description': ''},
    {'id': 6, 'url': 'http://cite.case.test:8000/ill/146/64/', 'name': 'City of Chicago v. Brownell',
     'citation': '146 Ill. 64', 'reporter': '', 'categories': [], 'jurisdiction': '', 'decision_date': '1893-06-19',
     'long_description': '', 'short_description': ''}
]
events = [
    {'id': 18, 'name': 'Event 6', 'color': '#00db67', 'end_date': '1878-12-31', 'start_date': '1875-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'},
    {'id': 25, 'name': 'Event 6', 'color': '#00B7DB', 'end_date': '1878-12-31', 'start_date': '1875-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'}
]
timeline_data = {"title": "My first timeline", "description": "And my very best one", "cases": cases, "events": events}


@pytest.mark.django_db
def test_uuid_workflow():
    timeline = Timeline(timeline=timeline_data)
    timeline.save()

    assert Timeline(timeline=timeline_data).objects.count() == 1

    timeline = Timeline(timeline=timeline_data)
    timeline.save()

    assert Timeline(timeline=timeline_data).objects.count() == 2






