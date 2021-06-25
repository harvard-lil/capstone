import pytest
from bs4 import BeautifulSoup
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
categories = [
    {'name': 'tesstcat', 'shape': 'polygon1', 'color': '#ff736c', 'id': 'arbitrary_string1'},
    {'name': 'tesstcat2', 'shape': 'polygon2', 'color': '#ff736c', 'id': 'arbitrary_string2'},
    {'name': 'tesstcat3', 'shape': 'polygon3', 'color': '#ff736c', 'id': 'arbitrary_string3'}
]
complete_timeline = {"title": "My first timeline",
                     "author": "CAP User",
                     "description": "And my very best one",
                     'events': events,
                     'cases': cases,
                     'categories': categories
                     }


@pytest.mark.django_db(databases=['default', 'capdb'])
def test_show_timelines(client, auth_client):
    # check to see it includes api urls since everything else is rendered in Vue
    response = client.get(reverse('labs:chronolawgic-dashboard'))
    check_response(response, content_includes="chronolawgic_api_create")
    soup = BeautifulSoup(response.content.decode(), 'html.parser')
    links = soup.find_all('a')
    login_link = None
    for link in links:
        if 'login/' in link.get('href'):
            login_link = link
            break
    assert login_link.get('href').split('?next=')[1] == reverse('labs:chronolawgic-dashboard')
    assert login_link and login_link.text.strip() == 'Log in'


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
    update_url = reverse('labs:chronolawgic-update-timeline-metadata', args=[tl.uuid])
    response = auth_client.post(update_url, timeline, format='json')
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == new_title

    new_title = "My third timeline attempt"
    timeline["title"] = new_title

    update_url = reverse('labs:chronolawgic-api-update', args=[tl.uuid])

    # don't allow unauthenticated users
    response = client.post(update_url, timeline, format='json')
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
    update_url = reverse('labs:chronolawgic-update-timeline-metadata', args=[tl.uuid])
    response = auth_client.post(update_url, tl.timeline, format='json')
    check_response(response, content_type="application/json")
    tl.refresh_from_db()

    # wrong data type will get replaced with default 'untitled timeline'
    tl.timeline['title'] = [1,2,3,4]
    tl.update_timeline_metadata(tl.timeline)
    response = auth_client.post(update_url, tl.timeline, format='json')
    check_response(response, status_code=200, content_type="application/json", content_includes='"title": "Untitled Timeline"')
    tl.refresh_from_db()

    # wrong data type for whole object will not get replaced
    update_url = reverse('labs:chronolawgic-api-add-update-subobject', args=[tl.uuid, 'events'])
    response = auth_client.post(update_url, [1, 2, 3, 4], format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes='Wrong Data Type for events entry')
    tl.refresh_from_db()


    # wrong data type for field object will not get replaced
    tl.timeline['events'][0]['id'] = [1,2,3,4]
    response = auth_client.post(update_url, tl.timeline['events'][0], format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes='Wrong Data Type for id')
    tl.refresh_from_db()

    # missing required case value
    del tl.timeline['cases'][0]['id']
    update_url = reverse('labs:chronolawgic-api-add-update-subobject', args=[tl.uuid, 'cases'])
    response = auth_client.post(update_url, tl.timeline['cases'][0], format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes="Missing cases field id")
    tl.refresh_from_db()

    # extraneous timeline field
    tl.timeline["helloooooo"] = "badata"
    update_url = reverse('labs:chronolawgic-update-timeline-metadata', args=[tl.uuid])
    response = auth_client.post(update_url, tl.timeline, format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes="Unexpected timeline field")
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

@pytest.mark.django_db(databases=['default', 'capdb'])
def test_update_categories(client, auth_client):
    tl = Timeline(
        created_by=auth_client.auth_user,
        timeline=Timeline.generate_empty_timeline(complete_timeline)
    )
    tl.save()

    categories_update = [
        {'name': 'tesstcat', 'shape': 'polygon1', 'color': '#ff736c', 'id': 'arbitrary_string1'},
        {'name': 'tesstcat9', 'shape': 'polygon2', 'color': '#ff736c', 'id': 'arbitrary_string2'},
        {'name': 'tesstcat3', 'shape': 'polygon3', 'color': '#ff736c', 'id': 'arbitrary_string3'}
    ]

    update_url = reverse('labs:chronolawgic-api-update-categories', args=[tl.uuid])
    response = auth_client.post(update_url, categories_update, format='json')
    check_response(response, content_type="application/json")
    tl.refresh_from_db()

    assert tl.timeline['categories'] == categories_update

    categories_update = [
        {'name': 'test', 'shape': 'polgon1', 'color': '#ff736c', 'id': 'arbitrary_string1'},
        {'name': 'tesstcat3', 'shape': 'polygon3', 'color': '#ff73c', 'id': 'arbitrary_string3'}
    ]

    response = auth_client.post(update_url, categories_update, format='json')
    check_response(response, content_type="application/json")
    tl.refresh_from_db()

    assert tl.timeline['categories'] == categories_update