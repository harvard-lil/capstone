from rest_framework import permissions
from django.utils.text import slugify


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

        # check whether user wants to get full case text
        context = view.get_renderer_context()
        full_case = context.get('request').query_params.get('full_case', 'false').lower()
        if full_case != 'true':
            # serve metadata to everyone!
            return True

        kwargs = context.get('kwargs')
        # get blacklisted case count
        if view.lookup_field in kwargs and '-' in slugify(kwargs[view.lookup_field]):
            # assume this is a lookup using a citation if hyphen is present
            cases = view.queryset.filter(citation__normalized_cite=slugify(kwargs[view.lookup_field]),
                                         jurisdiction__whitelisted=False)
        else:
            cases = view.queryset.filter(**kwargs, jurisdiction__whitelisted=False)

        blacklisted_count = cases.count()

        # If the request contains only whitelisted jurisdictions
        # serve up whether the user is signed in or not
        if not blacklisted_count:
            return True

        # from here forth one cannot be anonymous
        if request.user.is_anonymous():
            return False

        is_allowed = request.user.case_allowance_remaining >= blacklisted_count

        if is_allowed:
            # if allowed, discount the number of blacklisted cases served to the user
            request.user.update_case_allowance(case_count=blacklisted_count)
        return is_allowed

