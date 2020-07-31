import pytest


def test_admin_view__parallel(admin_client):
    response = admin_client.get('/admin/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_user_authenticate(admin_client, cap_user):
    """
    Test if we can activate users through the admin panel
    """
    cap_user.nonce_expires = None
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
