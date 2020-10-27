from pathlib import Path

import pytest
from django.conf import settings

import fabfile
from capapi import api_reverse
from capapi.tests.helpers import check_response


@pytest.mark.django_db
def test_ingest_courtlistener(client, elasticsearch):
    fabfile.ingest_courtlistener(Path(settings.BASE_DIR) / "test_data/courtlistener")
    response = client.get(api_reverse("resolve-list"), {'q': '254 P.3d 649'})
    check_response(response)
    assert response.json() == {
        '254 P.3d 649': [
            {
                'source': 'cl',
                'source_id': 891689,
                'citations': [
                    {
                        'cite': '254 P.3d 649',
                        'normalized_cite': '254p3d649',
                        'type': 3,
                        'volume': 254,
                        'reporter': 'P.3d',
                        'page': '649'
                    }
                ],
                'name_short': 'State v. Ramirez',
                'name_full': '',
                'decision_date': '2011-06-13',
                'frontend_url': 'https://www.courtlistener.com/opinion/891689/state-v-ramirez/',
                'api_url': 'https://www.courtlistener.com/api/rest/v3/clusters/891689/',
                'simhash': '1:b862eaa3efce3d01'
            }
        ]
    }
