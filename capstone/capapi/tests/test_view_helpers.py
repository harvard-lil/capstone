import pytest

from test_data.factories import *

from capapi import constants
from capapi.view_helpers import *


@pytest.mark.django_db
def test_get_whitelisted_case_filters():
    constants.OPEN_CASE_JURISDICTIONS = ['Illinois', 'Arkansas']
    jurisdiction = JurisdictionFactory(**{'name': 'New York'})

    for case in range(0, 2):
        setup_case(**{'jurisdiction': jurisdiction})

    whitelisted_filters = get_whitelisted_case_filters()
    all_cases = CaseMetadata.objects.all()
    assert all_cases.count() == all_cases.exclude(whitelisted_filters).count()

    jurisdiction = JurisdictionFactory(**{'name': 'Arkansas'})
    setup_case(**{'jurisdiction': jurisdiction})

    all_cases = CaseMetadata.objects.all()
    assert all_cases.count() != all_cases.exclude(whitelisted_filters).count()

