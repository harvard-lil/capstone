import django.shortcuts

import rest_framework.request
import rest_framework.reverse

from capapi.resources import TrackingWrapper, api_reverse
from capweb.helpers import reverse

# Monkeypatch rest_framework.request.Request to track accesses to request.user attributes.
# See capapi/middleware for rationale.
# This has to happen in __init__ because we have to monkeypatch DRF's Request object before it is imported by
# other modules.

OriginalRequest = rest_framework.request.Request

class CustomRequest(OriginalRequest):

    @OriginalRequest.user.setter
    def user(self, value):
        """
            Override DRF's Request.user setter to wrap the value in TrackingWrapper() so we can check later how it's
            accessed. "OriginalRequest.user.fset(self, value)" is equivalent to "super().user = value", except that
            super() doesn't work for overriding properties as opposed to methods.
        """
        OriginalRequest.user.fset(self, TrackingWrapper(value))

# make sure we only patch once if this module is re-imported
if OriginalRequest.__name__ != "CustomRequest":
    rest_framework.request.Request = CustomRequest

# Monkeypatch rest_framework.reverse._reverse to use our api_reverse function
rest_framework.reverse._reverse = api_reverse

# Monkeypatch django.shortcuts.resolve_url to use our reverse function
django.shortcuts.reverse = reverse
