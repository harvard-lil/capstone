from rest_framework import permissions

class IsSafeMethodsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # we're a read-only operation here
        # boot if user tries anything but `GET`, `OPTIONS`, or `HEAD`
        return request.method in permissions.SAFE_METHODS


class CanDownloadCaseExport(IsSafeMethodsUser):
    def has_object_permission(self, request, view, obj):
        return obj.public or request.user.unlimited_access_in_effect()
