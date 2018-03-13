from rest_framework import permissions


class AdminUserPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        return view.action == 'retrieve' or request.user.is_admin


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_admin


class IsAuthenticatedAPIUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.auth is not None


class IsSafeMethodsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # we're a read-only operation here
        # boot if user tries anything but `GET`, `OPTIONS`, or `HEAD`
        return request.method in permissions.SAFE_METHODS


casebody_permissions = [
    "OK; Whitelisted case",
    "OK; Your API limit has been updated",
    "Error; API token not provided",
    "Error; API case limit too low",
    "Error; Something went wrong"
]


def get_single_casebody_permissions(request, case):
    """
    field-level (casebody) permissions for user
    updating case download permissions for user if case is blacklisted
    """
    casebody = {"status": None, "data": None}

    if not case.jurisdiction:
        casebody["status"] = casebody_permissions[4]
        return casebody

    if not case.jurisdiction.whitelisted:
        if request.user.is_anonymous:
            casebody["status"] = casebody_permissions[2]
            return casebody
        else:
            request.user.update_case_allowance()
            if request.user.case_allowance_remaining < 1:
                casebody["status"] = casebody_permissions[3]
                return casebody
            else:
                request.user.update_case_allowance(case_count=1)
                casebody["status"] = casebody_permissions[1]
    else:
        casebody["status"] = casebody_permissions[0]

    return casebody
