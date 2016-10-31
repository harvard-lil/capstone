from rest_framework import permissions

class AdminUserPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        return view.action == 'retrieve' or request.user.is_admin

class IsAdminOrIsSelf(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_admin 
