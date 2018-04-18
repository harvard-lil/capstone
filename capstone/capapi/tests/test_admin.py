import pytest
from capapi.models import CapUser


def test_admin_view(admin_client):
    response = admin_client.get('/admin/')
    assert response.status_code == 200


def test_admin_user_create(admin_client):
    data = {
        "email": "bob_lawblaw@example.com",
        "first_name": "Bob",
        "last_name": "Lawblaw",
        "total_case_allowance": 500,
        "case_allowance_remaining": 500,
    }
    response = admin_client.post('/admin/capapi/capuser/add/', data, follow=True)
    assert response.status_code == 200
    user = CapUser.objects.get(email=data['email'])
    assert user


@pytest.mark.django_db
def test_admin_user_authenticate(admin_client, cap_user):
    """
    Test if we can authenticate user through the admin panel
    """
    data = {
        'action': 'authenticate_user',
        '_selected_action': cap_user.id,
    }
    response = admin_client.post('/admin/capapi/capuser/', data, follow=True)
    cap_user.refresh_from_db()

    assert response.status_code == 200
    assert cap_user.is_authenticated
    assert cap_user.get_api_key()


@pytest.mark.django_db
def test_admin_user_authenticate_without_key_expires(admin_client, cap_user):
    """
    Test if we can authenticate even if key_expires is missing
    """
    cap_user.key_expires = None
    cap_user.save()
    data = {
        'action': 'authenticate_user',
        '_selected_action': cap_user.id,
    }
    response = admin_client.post('/admin/capapi/capuser/', data, follow=True)
    cap_user.refresh_from_db()

    assert response.status_code == 200
    assert cap_user.is_authenticated
    assert cap_user.get_api_key()


