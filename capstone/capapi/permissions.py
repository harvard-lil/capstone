from rest_framework import permissions


class AdminUserPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        return view.action == 'retrieve' or request.user.is_admin


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_admin


class IsAPIUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method not in permissions.SAFE_METHODS:
            # we're a read-only operation here
            # boot if user tries anything but `GET`, `OPTIONS`, or `HEAD`
            return False

        # give away metadata to everyone!
        if not request.query_params.get('type') == 'download':
            return True
        else:
            # make sure user has auth token before proceeding if they want to download
            return request.auth
