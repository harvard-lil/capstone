import pytest
from capweb.helpers import reverse
from capapi.tests.helpers import check_response
from labs.models import Timeline

timeline = {"title": "My first timeline", "description": "And my very best one"}
create_url = reverse('labs:chronolawgic-api-create')
retrieve_url = reverse('labs:chronolawgic-api-retrieve')


@pytest.mark.django_db
def test_labs_page(client):
    response = client.get(reverse('labs:labs'))
    check_response(response, content_includes="CAP LABS")


@pytest.mark.django_db
def test_show_timelines(client, auth_client):
    response = client.get(reverse('labs:chronolawgic-dashboard'))
    # check to see it includes api urls since everything else is rendered in Vue
    check_response(response, content_includes="chronolawgic_api_create")


@pytest.mark.django_db
def test_create_timeline(client, auth_client):
    # should not allow timeline creation to not-authenticated users
    response = client.post(create_url, timeline)
    check_response(response, status_code=403, content_type="application/json")
    assert Timeline.objects.count() == 0

    response = auth_client.post(create_url, timeline)
    check_response(response, content_type="application/json")
    assert Timeline.objects.count() == 1


@pytest.mark.django_db
def test_timeline_retrieve(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)
    # allow retrieval by anyone
    response = client.get(retrieve_url + str(tl.id))
    check_response(response, content_type="application/json")
    timeline_response = response.json()["timeline"]
    # also of course by authenticated users
    response = auth_client.get(retrieve_url + str(tl.id))
    check_response(response, content_type="application/json")
    assert timeline_response["title"] == timeline["title"]

    # when no id is given
    # if non-authorized, show 403
    response = client.get(retrieve_url)
    check_response(response, status_code=403, content_type="application/json")

    # if authorized show all timelines when no id is given
    cases = ['case 1', 'case 2', 'case 3']
    events = ['event 1', 'event 2']
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


@pytest.mark.django_db
def test_timeline_update(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)
    response = auth_client.get(retrieve_url + str(tl.id))
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == timeline["title"]

    new_title = "My second timeline attempt"
    timeline["title"] = new_title
    update_url = reverse('labs:chronolawgic-api-update', args=[str(tl.id)])
    response = auth_client.post(update_url, {"timeline": timeline}, format='json')
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == new_title

    new_title = "My third timeline attempt"
    timeline["title"] = new_title

    update_url = reverse('labs:chronolawgic-api-update', args=[str(tl.id)])

    # don't allow unauthenticated users
    response = client.post(update_url, {"timeline": timeline}, format='json')
    check_response(response, status_code=403, content_type="application/json")

    response = auth_client.get(retrieve_url + str(tl.id))
    assert response.json()["timeline"]["title"] != timeline["title"]


@pytest.mark.django_db
def test_timeline_update_validation(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)
    update_url = reverse('labs:chronolawgic-api-update', args=[str(tl.id)])
    response = auth_client.post(update_url, {"timeline": {
        "description": "And my very best one"
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes="Timeline Missing")

    # missing timeline value
    response = auth_client.post(update_url, {"timeline": {
        "title": []
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Wrong Data Type for title")

    # wrong timeline value data type
    response = auth_client.post(update_url, {"timeline": {
        "title": []
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Wrong Data Type for title")

    # missing required case value
    response = auth_client.post(update_url, {"timeline": {
        "title": "Rad",
        "cases": [{'What even is': 'this?'}]
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json", content_includes="Case Missing: name")

    # wrong case data type
    response = auth_client.post(update_url, {"timeline": {
        "title": "Rad",
        "cases": [{'name': ['what', 'crazy', 'data', 'you', 'have']}]
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Case Has Wrong Data Type for name")

    # missing require event value
    response = auth_client.post(update_url, {
        "timeline": {
            "title": "Rad",
            "events": [{'name': 'wow', 'start_date': '1975-12-16'}]
        }
    }, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Event Missing: end_date")

    # wrong event data type
    response = auth_client.post(update_url, {"timeline": {
        "title": "Rad",
        "events": [{'name': 'wow', 'start_date': '1975-12-16', 'end_date': '1975-12-16',
                    'short_description': {'guess': 'who'}}]
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Event Has Wrong Data Type for short_description")

    # extraneous timeline field
    response = auth_client.post(update_url, {"timeline": {
        "title": "Rad",
        "events": [],
        "helloooooo": "badata"
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Unexpected timeline field(s)")

    # extraneous event field
    response = auth_client.post(update_url, {"timeline": {
        "title": "Rad",
        "events": [{'name': 'wow', 'start_date': '1975-12-16', 'end_date': '1975-12-16', 'DOESNOTBELONG': 'here'}],
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Unexpected event field(s)")

    # extraneous case field
    response = auth_client.post(update_url, {"timeline": {
        "title": "Rad",
        "cases": [{'name': 'joe v volcano', "herring_color": 'purple'}],
    }}, format='json')
    check_response(response, status_code=400, content_type="application/json",
                   content_includes="Unexpected case field(s)")


@pytest.mark.django_db
def test_timeline_delete(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)

    response = auth_client.get(retrieve_url + str(tl.id))
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == timeline["title"]

    delete_url = reverse('labs:chronolawgic-api-delete', args=[str(tl.id)])

    # don't allow unauthenticated users
    response = client.delete(delete_url)
    check_response(response, status_code=403, content_type="application/json")
    assert Timeline.objects.filter(created_by=auth_client.auth_user).count() == 1

    # allow authenticated creators of timeline
    response = auth_client.delete(delete_url)
    check_response(response, content_type="application/json")
    assert Timeline.objects.filter(created_by=auth_client.auth_user).count() == 0
