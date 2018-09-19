from django.conf import settings
from django_hosts import patterns, host

host_patterns = patterns('',
    host(r'', settings.ROOT_URLCONF, name='default'),
    host(r'api', 'capapi.api_urls', name='api'),
)