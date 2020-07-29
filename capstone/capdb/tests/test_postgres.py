from copy import deepcopy

import pytest
from django.db import transaction

from capapi.documents import CaseDocument
from capdb.models import CaseLastUpdate, CaseMetadata
from capdb.tasks import update_elasticsearch_from_queue
from scripts.helpers import parse_xml, serialize_xml


@pytest.mark.parametrize('versioned_fixture_name', [
    'volume_xml',
    'case_xml',
    'page_xml'
])
def test_versioning(transactional_db, versioned_fixture_name, request):
    # load initial volume_xml/case_xml/page_xml
    versioned_instance = request.getfixturevalue(versioned_fixture_name)
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


@pytest.mark.django_db(transaction=True)
def test_last_updated(case, extracted_citation_factory, elasticsearch):
    timestamp = None

    # helpers
    def get_timestamp():
        [[id, t]] = CaseLastUpdate.objects.values_list('case_id', 'timestamp')
        assert id == case.pk
        return t

    def check_timestamps_changed():
        nonlocal timestamp
        new_t = get_timestamp()
        assert timestamp < new_t
        timestamp = new_t

    def check_timestamps_unchanged():
        assert get_timestamp() == timestamp

    # creating case creates a timestamp
    timestamp = get_timestamp()

    # updating case field in set_up_postgres updates timestamp
    CaseMetadata.objects.filter(pk=case.id).update(frontend_url='foo')
    check_timestamps_changed()

    # updating case field not in set_up_postgres doesn't update timestamp
    CaseMetadata.objects.filter(pk=case.id).update(no_index_notes='foo')
    check_timestamps_unchanged()

    # adding inbound references
    extracted_cite = extracted_citation_factory(cited_by=case)
    check_timestamps_changed()

    # updating inbound references
    for obj, change_field, no_change_field in (
            (case.citations.first(), 'cite', 'normalized_cite'),
            (case.body_cache, 'html', 'text'),
            (extracted_cite, 'cite', 'normalized_cite'),
    ):
        # updating tracked field
        setattr(obj, change_field, 'foo')
        obj.save()
        check_timestamps_changed()

        # updated untracked field
        setattr(obj, no_change_field, 'foo')
        obj.save()
        check_timestamps_unchanged()

        # deleting
        obj.delete()
        check_timestamps_changed()

    # updating outbound references
    for obj, change_field, no_change_field in (
        (case.reporter, 'full_name', 'short_name'),
        (case.court, 'name', 'none'),
        (case.volume, 'volume_number', 'publisher'),
        (case.jurisdiction, 'name', 'none'),
    ):
        # updating tracked field
        setattr(obj, change_field, 'foo')
        obj.save()
        check_timestamps_changed()

        # updated untracked field
        setattr(obj, no_change_field, 'foo')
        obj.save()
        check_timestamps_unchanged()

    # case gets removed when in_scope changes
    update_elasticsearch_from_queue()
    CaseDocument.get(case.pk)
    case.duplicative = True
    case.save()
    update_elasticsearch_from_queue()
    CaseDocument.get(case.pk)
