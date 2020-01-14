from rest_framework import permissions

from capdb.models import CaseMetadata


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
    if 'id' not in case.jurisdiction:
        status = "error_unknown"

    elif case.jurisdiction['whitelisted']:
        status = "ok"

    elif request.user.is_anonymous:
        status = "error_auth_required"

    elif request.site_limits.daily_downloads >= request.site_limits.daily_download_limit:
        status = "error_sitewide_limit_exceeded"

    elif 'recovery_key' in request.GET:
        if CaseMetadata(id=case.id).valid_recovery_key(request.user, request.GET['recovery_key']):
            status = "ok"
        else:
            status = "error_invalid_recovery_key"

    else:
        try:
            request.user.update_case_allowance(case_count=1, save=False)
            status = "ok"
        except AttributeError:
            status = "error_limit_exceeded"

    return status
