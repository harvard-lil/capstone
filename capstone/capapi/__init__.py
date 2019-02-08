import django.shortcuts
import rest_framework.reverse

from capapi.resources import api_reverse
from capweb.helpers import reverse

# Monkeypatch rest_framework.reverse._reverse to use our api_reverse function
rest_framework.reverse._reverse = api_reverse

# Monkeypatch django.shortcuts.resolve_url to use our reverse function
django.shortcuts.reverse = reverse
