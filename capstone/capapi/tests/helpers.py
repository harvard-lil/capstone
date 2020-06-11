import fitz

from django.conf import settings
from rest_framework.response import Response


def check_response(response, status_code=200, content_type=None, content_includes=None, content_excludes=None):
    assert response.status_code == status_code

    # check content-type if not a redirect
    if response['content-type']:
        # For rest framework response, expect json; else expect html.
        if not content_type:
            if type(response) == Response:
                content_type = "application/json"
            else:
                content_type = "text/html"
        assert response['content-type'].split(';')[0] == content_type

    if content_includes or content_excludes:

        if content_type == 'application/pdf':
            content = "\n".join(page.getText() for page in fitz.open(stream=response.content, filetype="pdf"))
        else:
            try:
                content = response.content.decode()
            except AttributeError:
                # FileResponse
                content = b''.join(response.streaming_content).decode()

        if content_includes:
            if isinstance(content_includes, str):
                content_includes = [content_includes]
            for content_include in content_includes:
                assert content_include in content

        if content_excludes:
            if isinstance(content_excludes, str):
                content_excludes = [content_excludes]
            for content_exclude in content_excludes:
                assert content_exclude not in content


def is_cached(response):
    cache_header = response['cache-control'] if response.has_header('cache-control') else ''
    return 's-maxage=%d' % settings.CACHE_CONTROL_DEFAULT_MAX_AGE in cache_header