from copy import deepcopy

import pytest
from django.db import transaction

from scripts.helpers import parse_xml, serialize_xml


@pytest.mark.parametrize('versioned_fixture_name', [
    'volume_xml',
    'case_xml',
    'page_xml'
])
def test_versioning(transactional_db, versioned_fixture_name, request):
    # load initial volume_xml/case_xml/page_xml
    versioned_instance = request.getfuncargvalue(versioned_fixture_name)
    original_instance = deepcopy(versioned_instance)

    # starts with no history
    assert versioned_instance.history.count() == 0

    # versions are only created once per transaction.
    # since tests run in transactions, run an initial sub-transaction to
    # make sure our next save causes a new version to be created.
    # note that this is not sufficient when using the temporal_tables
    # extension, which additionally requires (transaction=True) as an
    # argument to the pytest.mark.django_db decorator
    with transaction.atomic(using='capdb'):
        versioned_instance.save()

    # make some modifications:
    versioned_instance.s3_key = 'changed'
    parsed = parse_xml(versioned_instance.orig_xml)
    parsed('mets').append("<new_element/>")
    versioned_instance.orig_xml = serialize_xml(parsed)

    # save modified version:
    with transaction.atomic(using='capdb'):
        versioned_instance.save()

    # historical version should now exist:
    previous_version = versioned_instance.history.first()
    assert previous_version

    # current version's sys_period should start where historical version's sys_period ends:
    versioned_instance.refresh_from_db()  # load current sys_period
    assert versioned_instance.sys_period.lower == previous_version.sys_period.upper

    # historical version should have values from before latest save:
    assert previous_version.s3_key == original_instance.s3_key
    assert previous_version.orig_xml == original_instance.orig_xml
