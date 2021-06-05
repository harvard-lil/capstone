import pytest
import copy
from capweb.helpers import reverse
from capapi.tests.helpers import check_response
from labs.models import Timeline


timeline = {"title": "My first timeline", "author": "CAP User", "description": "And my very best one"}
create_url = reverse('labs:chronolawgic-api-create')
retrieve_url = reverse('labs:chronolawgic-api-retrieve')
cases = [
    {'id': 'abc1', 'url': 'https://cite.case.law/ill/1/176/', 'name': 'Case 2', 'citation': '1 Mass. 1',
     'reporter': "Abb. Pr.- Abbott's Practice Reports", 'jurisdiction': 'California',
     'decision_date': '1898-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'},
    {'id': 'abc2', 'url': 'http://cite.case.test:8000/ill-app-2d/59/188/', 'name': 'Gurshey v. Chicago Transit Authority',
     'citation': '59 Ill. App. 2d 188', 'reporter': '', 'categories': [], 'jurisdiction': '',
     'decision_date': '1965-05-10', 'long_description': '', 'short_description': ''},
    {'id': 'abc3', 'url': 'http://cite.case.test:8000/ill/146/64/', 'name': 'City of Chicago v. Brownell',
     'citation': '146 Ill. 64', 'reporter': '', 'categories': [], 'jurisdiction': '', 'decision_date': '1893-06-19',
     'long_description': '', 'short_description': ''}
]
events = [
    {'id': 'abc4', 'name': 'Event 6', 'color': '#00db67', 'end_date': '1878-12-31', 'start_date': '1875-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'},
    {'id': 'abc5', 'name': 'Event 6', 'color': '#00B7DB', 'end_date': '1878-12-31', 'start_date': '1875-12-31',
     'long_description': 'abcdefghijklmnopqrstuvwxyz',
     'short_description': 'abc'}
]
complete_timeline = {"title": "My first timeline", "author": "CAP User", "description": "And my very best one", 'events': events, 'cases': cases}


@pytest.mark.django_db(databases=['default', 'capdb'])
def test_show_timelines(client, auth_client):
    response = client.get(reverse('labs:chronolawgic-dashboard'))
    # check to see it includes api urls since everything else is rendered in Vue
    check_response(response, content_includes="chronolawgic_api_create")


@pytest.mark.django_db(databases=['default'])
def test_create_timeline(client, auth_client):
    # should not allow timeline creation to not-authenticated users
    response = client.post(create_url, timeline)
    check_response(response, status_code=403, content_type="application/json")
    assert Timeline.objects.count() == 0

    response = auth_client.post(create_url, timeline)
    check_response(response, content_type="application/json")
    assert Timeline.objects.count() == 1
    # assert categories exist
    assert Timeline.objects.first().timeline['categories'] == []


@pytest.mark.django_db(databases=['default'])
def test_clobber_stopper(auth_client):
    # should not allow editing more than 1 case or event per request
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=complete_timeline)

    # modify one event field
    modified_timeline = copy.deepcopy(complete_timeline)
    modified_timeline['events'][0]['name'] = 'another name'

    # one field in one event different from the DB version— no problem
    update_url = reverse('labs:chronolawgic-api-update', args=[tl.uuid])
    response = auth_client.post(update_url, {"timeline": modified_timeline}, format='json')
    check_response(response, content_type="application/json")

    # last test modified timeline, so change it back
    tl.timeline = complete_timeline
    tl.save()

    # modify three event fields – no problem
    modified_timeline = copy.deepcopy(complete_timeline)
    modified_timeline['events'][0]['name'] = 'another name'
    modified_timeline['events'][0]['end_date'] = '1848-12-31'
    modified_timeline['events'][0]['short_description'] = '1999-12-31'
    response = auth_client.post(update_url, {"timeline": modified_timeline}, format='json')
    check_response(response, content_type="application/json")
    tl.timeline = complete_timeline
    tl.save()

    #modify one case field – no problem
    modified_timeline = copy.deepcopy(complete_timeline)
    modified_timeline['cases'][0]['name'] = 'another name'
    response = auth_client.post(update_url, {"timeline": modified_timeline}, format='json')
    check_response(response, content_type="application/json")
    tl.timeline = complete_timeline
    tl.save()

    # modify three case fields - no problem
    modified_timeline = copy.deepcopy(complete_timeline)
    modified_timeline['cases'][0]['name'] = 'another name'
    modified_timeline['cases'][0]['decision_date'] = '1848-12-31'
    modified_timeline['cases'][0]['short_description'] = '1999-12-31'
    response = auth_client.post(update_url, {"timeline": modified_timeline}, format='json')
    check_response(response, content_type="application/json")
    tl.timeline = complete_timeline
    tl.save()

    #modify two cases - problem
    modified_timeline = copy.deepcopy(complete_timeline)
    modified_timeline['cases'][0]['name'] = 'another name'
    modified_timeline['cases'][1]['short_description'] = '1999-12-31'
    response = auth_client.post(update_url, {"timeline": modified_timeline}, format='json')
    check_response(response, status_code=500, content_type="application/json")

    # modify two events - problem
    modified_timeline = copy.deepcopy(complete_timeline)
    modified_timeline['events'][0]['name'] = 'another name'
    modified_timeline['events'][1]['end_date'] = '1848-12-31'
    response = auth_client.post(update_url, {"timeline": modified_timeline}, format='json')
    check_response(response, status_code=500, content_type="application/json")

    # modify case and event - problem
    modified_timeline = copy.deepcopy(complete_timeline)
    modified_timeline['events'][0]['name'] = 'another name'
    modified_timeline['cases'][1]['short_description'] = '1999-12-31'
    response = auth_client.post(update_url, {"timeline": modified_timeline}, format='json')
    check_response(response, status_code=500, content_type="application/json")


@pytest.mark.django_db(databases=['default'])
def test_timeline_retrieve(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)
    # allow retrieval by anyone
    response = client.get(retrieve_url + tl.uuid)
    check_response(response, content_type="application/json")
    timeline_response = response.json()["timeline"]
    # also of course by authenticated users
    response = auth_client.get(retrieve_url + tl.uuid)
    check_response(response, content_type="application/json")
    assert timeline_response["title"] == timeline["title"]

    # when no id is given
    # if non-authorized, show no timelines, 200
    response = client.get(retrieve_url)
    check_response(response, content_type="application/json")

    # if authorized show all timelines when no id is given
    timeline['cases'] = cases
    timeline['events'] = events
    tl.timeline = timeline
    tl.save()

    response = auth_client.get(retrieve_url)
    timelines_response = response.json()["timelines"]
    assert len(timelines_response) == 1
    assert timelines_response[0]["title"] == timeline["title"]
    assert timelines_response[0]["case_count"] == len(cases)
    assert timelines_response[0]["event_count"] == len(events)


@pytest.mark.django_db(databases=['default'])
def test_timeline_update(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)
    response = auth_client.get(retrieve_url + tl.uuid)
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == timeline["title"]

    new_title = "My second timeline attempt"
    timeline["title"] = new_title
    update_url = reverse('labs:chronolawgic-api-update', args=[tl.uuid])
    response = auth_client.post(update_url, {"timeline": timeline}, format='json')
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == new_title

    new_title = "My third timeline attempt"
    timeline["title"] = new_title

    update_url = reverse('labs:chronolawgic-api-update', args=[tl.uuid])

    # don't allow unauthenticated users
    response = client.post(update_url, {"timeline": timeline}, format='json')
    check_response(response, status_code=403, content_type="application/json")

    response = auth_client.get(retrieve_url + tl.uuid)
    assert response.json()["timeline"]["title"] != timeline["title"]


@pytest.mark.django_db(databases=['default'])
def test_timeline_update_validation(client, auth_client):
    tl = Timeline()
    tl.created_by = auth_client.auth_user
    tl.timeline = complete_timeline
    tl.save()

    tl.timeline['description'] = "And my very best on"
    update_url = reverse('labs:chronolawgic-api-update', args=[tl.uuid])
    response = auth_client.post(update_url, {"timeline": tl.timeline}, format='json')
    check_response(response, content_type="application/json")
    tl.refresh_from_db()

    tl.timeline['description'] = "And my very best"
    tl.timeline['author'] = "And my very bet"
    update_url = reverse('labs:chronolawgic-api-update', args=[tl.uuid])
    response = auth_client.post(update_url, {"timeline": tl.timeline}, format='json')
    check_response(response, status_code=500, content_type="application/json", content_includes="More than one change or remove detected")
    tl.refresh_from_db()

    # wrong data type will get replaced with default 'untitled timeline'
    tl.timeline['title'] = [1,2,3,4]
    response = auth_client.post(update_url, {"timeline": tl.timeline}, format='json')
    check_response(response, status_code=200, content_type="application/json", content_includes='"title": "Untitled Timeline"')
    tl.refresh_from_db()

    # wrong data type for whole object will not get replaced
    tl.timeline['events'][0] = [1,2,3,4]
    response = auth_client.post(update_url, {"timeline": tl.timeline}, format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes='Wrong Data Type for event entry')
    tl.refresh_from_db()

    # wrong data type for whole object will not get replaced
    tl.timeline['events'][0]['id'] = [1,2,3,4]
    response = auth_client.post(update_url, {"timeline": tl.timeline}, format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes='Wrong Data Type')
    tl.refresh_from_db()

    # missing required case value
    del tl.timeline['cases'][0]['id']
    response = auth_client.post(update_url, {"timeline": tl.timeline}, format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes="Missing case field id")
    tl.refresh_from_db()

    # extraneous timeline field
    tl.timeline["helloooooo"] = "badata"
    response = auth_client.post(update_url, {"timeline": tl.timeline}, format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes="Unexpected timeline field(s)")
    tl.refresh_from_db()
    assert "helloooooo" not in tl.timeline



@pytest.mark.django_db(databases=['default'])
def test_timeline_delete(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)

    response = auth_client.get(retrieve_url + tl.uuid)
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == timeline["title"]

    delete_url = reverse('labs:chronolawgic-api-delete', args=[tl.uuid])

    # don't allow unauthenticated users
    response = client.delete(delete_url)
    check_response(response, status_code=403, content_type="application/json")
    assert Timeline.objects.filter(created_by=auth_client.auth_user).count() == 1

    # allow authenticated creators of timeline
    response = auth_client.delete(delete_url)
    check_response(response, content_type="application/json")
    assert Timeline.objects.filter(created_by=auth_client.auth_user).count() == 0
