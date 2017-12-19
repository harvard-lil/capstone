def check_response(response, status_code=200, format='json'):
    assert response.status_code == status_code
    if format:
        assert response.accepted_renderer.format == format

