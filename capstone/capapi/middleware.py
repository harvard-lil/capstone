import logging
import re

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

def add_cache_header(response, s_maxage=settings.CACHE_CONTROL_DEFAULT_MAX_AGE):
    patch_cache_control(response, s_maxage=s_maxage)

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

        # do nothing if s-maxage already set
        if response.has_header("Cache-Control") and 's-maxage' in response['cache-control'].lower():
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
                (
                    # if user failed to authenticate, we can only cache if they
                    # didn't supply a bad sessionid cookie or authorization header
                    'HTTP_AUTHORIZATION' not in request.META
                    and settings.SESSION_COOKIE_NAME not in request.COOKIES
                ) if (not hasattr(request, 'user') or request.user.is_anonymous) else (
                    # if user successfully authenticated, we can only cache if we
                    # didn't access any user-specific data in preparing this view
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
            add_cache_header(response)
        else:
            add_cache_header(response, s_maxage=0)

        return response

    return middleware

# To decide on caching we have to wrap request.user in TrackingWrapper so we can check what user data is accessed
# by the view. That's done here, and also in capapi/__init__.py as a monkeypatch to DRF.

class AuthenticationMiddleware(DjangoAuthenticationMiddleware):
    def process_request(self, request):
        super().process_request(request)
        request.user = TrackingWrapper(request.user)
        request.user.ip_address = request.META.get('HTTP_X_FORWARDED_FOR')  # used by user IP auth checks


# see https://stackoverflow.com/a/35928017
#     https://docs.djangoproject.com/en/2.0/topics/http/middleware/
#     https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.35
class RangeRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # is this request eligible for a range request?
        if response.status_code != 200 or not hasattr(response, 'file_to_stream'):
            return response

        # parse the range(s) -- at the moment, we're only responding to the
        # first range, but we coalesce adjacent and overlapping ranges below
        http_range = request.META.get('HTTP_RANGE')
        units = "bytes="
        if http_range and http_range.startswith(units):
            ranges = []
            matches = re.finditer(r"(\d*)-(\d*),?", http_range[len(units):])
            if matches:
                # treat the response as a file so we can see how big it is
                f = response.file_to_stream
                # response_size = os.fstat(f.fileno()).st_size
                response_size = f.size
            for match in matches:
                start = match.group(1)
                end = match.group(2)
                # the case where both ends of the range are empty
                if not start and not end:
                    continue
                # the case where start is empty
                if not start:
                    start = max(0, response_size - int(end))
                else:
                    start = int(start)
                # this handles the case where end is empty and where it isn't
                end = int(end or response_size - 1)
                if start >= response_size or start > end:
                    response.status_code = 416
                    response['Content-Range'] = 'bytes */%d' % response_size
                    return response
                end = min(end, response_size - 1)
                ranges.append((start, end))
        else:
            return response

        # we're not really handling If-Range headers; if present and ill-formed,
        # return the whole content
        if_range = request.META.get('HTTP_IF_RANGE')
        if if_range and if_range != response.get('Last-Modified') and if_range != response.get('ETag'):
            return response

        # coalesce adjacent and overlapping ranges
        collapsed_ranges = []
        for cur in sorted(ranges):
            if len(collapsed_ranges) == 0:
                collapsed_ranges.append(cur)
            else:
                prev = collapsed_ranges.pop()
                if cur[0] - 1 <= prev[1]:
                    collapsed_ranges.append((prev[0], max(prev[1], cur[1])))
                else:
                    collapsed_ranges.append(prev)
                    collapsed_ranges.append(cur)
        ranges = collapsed_ranges

        # to handle more than the first range, we'd need to produce a
        # multipart response...
        if len(ranges) > 0:
            (start, end) = ranges[0]

            # iterator for range of file
            def fchunks(start, end):
                counter = 0
                for chunk in f.chunks(chunk_size=1):
                    if counter < start:
                        pass
                    elif start <= counter and counter <= end:
                        yield chunk
                    elif counter > end:
                        return
                    counter = counter + 1

            response.streaming_content = fchunks(start, end)
            response.status_code = 206
            response['Content-Length'] = end + 1 - start
            response['Content-Range'] = 'bytes %d-%d/%d' % (start, end, response_size)
        return response
