from capweb.helpers import reverse
from capapi.tests.helpers import check_response


def test_labs_page(client):
    response = client.get(reverse('labs:labs'))
    check_response(response, content_includes="A space for CAP experiments.")


