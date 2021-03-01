import pytest
import json
from capweb.helpers import reverse
from capapi.tests.helpers import check_response
from labs.models import Timeline

timeline = {"title": "My first timeline", "subhead": "And my very best one"}
create_url = reverse('labs:chronolawgic-api-create')
retrieve_url = reverse('labs:chronolawgic-api-retrieve')


@pytest.mark.django_db
def test_labs_page(client):
    response = client.get(reverse('labs:labs'))
    check_response(response, content_includes="CAP LABS")


@pytest.mark.django_db
def test_show_timelines(client, auth_client, jurisdiction):
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
    assert response.json()["timeline"]["title"] == timeline["title"]

    # also of course by authenticated users
    response = auth_client.get(retrieve_url + str(tl.id))
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == timeline["title"]


@pytest.mark.django_db
def test_timeline_update(client, auth_client):
    tl = Timeline.objects.create(created_by=auth_client.auth_user, timeline=timeline)
    response = auth_client.get(retrieve_url + str(tl.id))
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == timeline["title"]

    new_title = "My second timeline attempt"
    timeline["title"] = new_title

    update_url = reverse('labs:chronolawgic-api-update', args=[str(tl.id)])
    response = auth_client.post(update_url, {"timeline": json.dumps(timeline)})
    check_response(response, content_type="application/json")
    assert response.json()["timeline"]["title"] == new_title

    new_title = "My third timeline attempt"
    timeline["title"] = new_title

    update_url = reverse('labs:chronolawgic-api-update', args=[str(tl.id)])

    # don't allow unauthenticated users
    response = client.post(update_url, {"timeline": json.dumps(timeline)})
    check_response(response, status_code=403, content_type="application/json")

    response = auth_client.get(retrieve_url + str(tl.id))
    assert response.json()["timeline"]["title"] != timeline["title"]


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