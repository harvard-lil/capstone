from labs.helpers.chronolawgic import validate_and_normalize_timeline, TimelineValidationException
from pytest import raises
from copy import deepcopy

timeline = {
    "title": "My first timeline",
    "description": "And my very best one",
    "author": "CAP User",
    "cases": [
        {'id': 'abc1', 'url': 'https://cite.case.law/ill/1/176/', 'name': 'Case 2', 'citation': '1 Mass. 1',
         'reporter': "Abb. Pr.- Abbott's Practice Reports", 'jurisdiction': 'California',
         'decision_date': '1898-12-31',
         'long_description': 'abcdefghijklmnopqrstuvwxyz',
         'short_description': 'abc'},
        {'id': 'abc2', 'url': 'http://cite.case.test:8000/ill-app-2d/59/188/',
         'name': 'Gurshey v. Chicago Transit Authority',
         'citation': '59 Ill. App. 2d 188', 'reporter': '', 'categories': [], 'jurisdiction': '',
         'decision_date': '1965-05-10', 'long_description': '', 'short_description': ''},
        {'id': 'abc3', 'url': 'http://cite.case.test:8000/ill/146/64/', 'name': 'City of Chicago v. Brownell',
         'citation': '146 Ill. 64', 'reporter': '', 'categories': [], 'jurisdiction': '', 'decision_date': '1893-06-19',
         'long_description': '', 'short_description': ''}
    ], "events": [
        {'id': 'abc4', 'name': 'Event 6', 'color': '#00db67', 'end_date': '1878-12-31', 'start_date': '1875-12-31',
         'long_description': 'abcdefghijklmnopqrstuvwxyz',
         'short_description': 'abc'},
        {'id': 'abc5', 'name': 'Event 6', 'color': '#00B7DB', 'end_date': '1878-12-31', 'start_date': '1875-12-31',
         'long_description': 'abcdefghijklmnopqrstuvwxyz',
         'short_description': 'abc'}
    ]
}

def test_validate_timeline():
    # assert no bad values
    assert validate_and_normalize_timeline(timeline) == timeline

    # assert bad value in cases
    bad_timeline_1 = deepcopy(validate_and_normalize_timeline(timeline))
    bad_timeline_1["cases"][0]["bad"] = "value"
    with raises(TimelineValidationException, match=r".*Unexpected case field\(s\): \{'bad'\}.*"):
        validate_and_normalize_timeline(bad_timeline_1)

    # assert bad value in events
    bad_timeline_2 = deepcopy(validate_and_normalize_timeline(timeline))
    bad_timeline_2["events"][0]["bad"] = "value"
    with raises(TimelineValidationException, match=r".*Unexpected event field\(s\): \{'bad'\}.*"):
        validate_and_normalize_timeline(bad_timeline_2)
