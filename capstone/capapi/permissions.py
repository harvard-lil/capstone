from rest_framework import permissions


staff_level_permissions = [
    'capdb.change_jurisdiction',
    'capapi.add_capuser',
    'capapi.change_capuser',
    'capapi.delete_capuser',
]


class IsAuthenticatedCapUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.auth is not None


class IsSafeMethodsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # we're a read-only operation here
        # boot if user tries anything but `GET`, `OPTIONS`, or `HEAD`
        return request.method in permissions.SAFE_METHODS


casebody_permissions = ["ok", "error_auth_required", "error_limit_exceeded", "error_unknown"]


def get_single_casebody_permissions(request, case):
    """
    field-level (casebody) permissions for user
    updating case download permissions for user if case is blacklisted
    """
    casebody = {"status": None, "data": None}

    if not case.jurisdiction_id:
        casebody["status"] = casebody_permissions[3]
        return casebody

    if case.jurisdiction_whitelisted:
        casebody["status"] = casebody_permissions[0]
        return casebody

    if request.user.is_anonymous:
        casebody["status"] = casebody_permissions[1]
    else:
        try:
            request.user.update_case_allowance(case_count=1, save=False)
            casebody["status"] = casebody_permissions[0]
        except AttributeError:
            casebody["status"] = casebody_permissions[2]

    return casebody
