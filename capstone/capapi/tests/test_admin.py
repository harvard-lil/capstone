import pytest
from capapi.permissions import staff_level_permissions

from django.contrib.auth.models import Permission


def test_admin_view(admin_client):
    response = admin_client.get('/admin/')
    assert response.status_code == 200


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
def test_admin_user_authenticate_without_nonce_expires(admin_client, cap_user):
    """
    Test if we can authenticate even if nonce_expires is missing
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


@pytest.mark.django_db
def test_staff_permissions(staff_user):
    permissions = Permission.objects.all()
    for perm in permissions:
        action, app, table = perm.natural_key()
        perm_str = "%s.%s" % (app, action)
        if perm_str in staff_level_permissions:
            assert staff_user.has_perm(perm_str)
        else:
            assert staff_user.has_perm(perm_str) is False

    # downgrade staff to regular user
    staff_user.is_staff = False
    staff_user.save()
    permissions = Permission.objects.all()
    for perm in permissions:
        action, app, table = perm.natural_key()
        perm_str = "%s.%s" % (app, action)
        assert staff_user.has_perm(perm_str) is False


@pytest.mark.django_db
def test_admin_permissions(admin_user):
    permissions = Permission.objects.all()
    for perm in permissions:
        action, app, table = perm.natural_key()
        perm_str = "%s.%s" % (app, action)
        assert admin_user.has_perm(perm_str)


@pytest.mark.django_db
def test_user_permissions(cap_user):
    cap_user.is_staff = False
    cap_user.save()
    permissions = Permission.objects.all()
    for perm in permissions:
        action, app, table = perm.natural_key()
        perm_str = "%s.%s" % (app, action)
        assert cap_user.has_perm(perm_str) is False

