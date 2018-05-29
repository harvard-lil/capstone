import logging

from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware as DjangoAuthenticationMiddleware
from django.utils.cache import patch_cache_control

from capapi import TrackingWrapper

logger = logging.getLogger(__name__)


### cache_header_middleware ###

# Accessing one of these attributes on request.user does NOT indicate that the view contains user-specific data.
# Accessing any attributes other than these will prevent caching.
_capuser_cache_safe_attributes = {
    'is_anonymous', 'is_authenticated', '__class__',
}

def cache_header_middleware(get_response):
    """
        Set an outgoing "Cache-Control: s-maxage=<settings.CACHE_CONTROL_DEFAULT_MAX_AGE>" header on all requests
        that are detected to be cacheable.

        See test_cache.py for examples of when we set or don't set cache headers.

        IMPORTANT: We assume that there is a downstream cache proxy sorting logged-in and logged-out users into two
        separate cache buckets. This middleware should only be used with such a proxy; otherwise it will cause
        logged-in users to sometimes see cached content for logged-out users and vice versa. (Even then it should never
        cause logged-out users to see information belonging to specific logged-in users, however, as accessing
        request.user prevents caching.)
    """

    def middleware(request):
        response = get_response(request)

        if not settings.SET_CACHE_CONTROL_HEADER:
            return response

        # To cache this response, all of these must be true:
        # - The user is undefined or anonymous or has not accessed any user-specific attributes.
        # - The request method is GET, HEAD, or OPTIONS.
        # - The Cache-Control header was not already set.
        #   (Setting that header happens when Django is trying to protect something.)
        # - CSRF protection is not being used for this view.
        # - No cookies are set by this view.
        view_tests = {
            'user_safe': (
                not hasattr(request, 'user')
                or request.user.is_anonymous
                or (
                    hasattr(request.user, '_self_accessed_attrs')
                    and not (request.user._self_accessed_attrs - _capuser_cache_safe_attributes)
                )
            ),
            'method': request.method in ('GET', 'HEAD', 'OPTIONS'),
            'cache_header_not_set': not response.has_header("Cache-Control"),
            'csrf_cookie_not_used': not request.META.get("CSRF_COOKIE_USED"),
            'cookie_header_not_set': not response.has_header("Set-Cookie"),
        }

        # If all tests pass, we can set the Cache-Control header
        cache_response = all(view_tests.values())
        logger.info("Cacheable response: %s (%s)" % (cache_response, view_tests))
        if cache_response:
            patch_cache_control(response, s_maxage=settings.CACHE_CONTROL_DEFAULT_MAX_AGE)
        else:
            patch_cache_control(response, s_maxage=0)

        return response

    return middleware

# To decide on caching we have to wrap request.user in TrackingWrapper so we can check what user data is accessed
# by the view. That's done here, and also in capapi/__init__.py as a monkeypatch to DRF.

class AuthenticationMiddleware(DjangoAuthenticationMiddleware):
    def process_request(self, request):
        super().process_request(request)
        request.user = TrackingWrapper(request.user)

