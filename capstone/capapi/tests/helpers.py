from rest_framework.response import Response


def check_response(response, status_code=200, content_type=None, content_includes=None):
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

    if content_includes:
        assert content_includes in response.content.decode()

