from rest_framework import permissions

class IsSafeMethodsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # we're a read-only operation here
        # boot if user tries anything but `GET`, `OPTIONS`, or `HEAD`
        return request.method in permissions.SAFE_METHODS


class CanDownloadCaseExport(IsSafeMethodsUser):
    def has_object_permission(self, request, view, obj):
        return obj.public or request.user.unlimited_access_in_effect()


def check_update_case_permissions(request, case):
    """
        checks permissions, returns a status, and if appropriate, updates allowance
    """

    casebody_permissions = {
        "ok": "ok",
        "auth": "error_auth_required",
        "limit": "error_limit_exceeded",
        "unk": "error_unknown",
        "sitelimit": "error_sitewide_limit_exceeded"
    }
    if 'id' not in case.jurisdiction:
        status = casebody_permissions["unk"]

    elif case.jurisdiction['whitelisted']:
        status = casebody_permissions["ok"]

    elif request.user.is_anonymous:
        status = casebody_permissions["auth"]

    elif request.site_limits.daily_downloads >= request.site_limits.daily_download_limit:
        status = casebody_permissions["sitelimit"]

    else:
        try:
            request.user.update_case_allowance(case_count=1, save=False)
            status = casebody_permissions["ok"]
        except AttributeError:
            status = casebody_permissions["limit"]

    return status
