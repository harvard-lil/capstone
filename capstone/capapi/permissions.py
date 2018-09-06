from rest_framework import permissions


staff_level_permissions = [
    'capdb.change_jurisdiction',
    'capapi.add_capuser',
    'capapi.change_capuser',
    'capapi.delete_capuser',
]


class IsSafeMethodsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # we're a read-only operation here
        # boot if user tries anything but `GET`, `OPTIONS`, or `HEAD`
        return request.method in permissions.SAFE_METHODS


class CanDownloadCaseExport(IsSafeMethodsUser):
    def has_object_permission(self, request, view, obj):
        return obj.public or request.user.unlimited_access_in_effect()


casebody_permissions = ["ok", "error_auth_required", "error_limit_exceeded", "error_unknown", "error_sitewide_limit_exceeded"]


def get_single_casebody_permissions(request, case):
    """
    field-level (casebody) permissions for user
    updating case download permissions for user if case is blacklisted
    """
    casebody = {"status": None, "data": None}

    if not case.jurisdiction_id:
        casebody["status"] = casebody_permissions[3]

    elif case.jurisdiction_whitelisted:
        casebody["status"] = casebody_permissions[0]

    elif request.user.is_anonymous:
        casebody["status"] = casebody_permissions[1]

    elif request.site_limits.daily_downloads >= request.site_limits.daily_download_limit:
        casebody["status"] = casebody_permissions[4]

    else:
        try:
            request.user.update_case_allowance(case_count=1, save=False)
            casebody["status"] = casebody_permissions[0]
        except AttributeError:
            casebody["status"] = casebody_permissions[2]

    return casebody
