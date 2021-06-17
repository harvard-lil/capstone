import pytest

from capweb.templatetags.cached_json_object import cached_json_object

@pytest.mark.django_db(databases=['capdb'])
def test_cached_json(client, django_assert_num_queries):
    cjo_labels = ['map_numbers', 'search_jurisdiction_list', 'search_court_list', 'search_reporter_list',
               'court_abbrev_list']

    for cjo_label in cjo_labels:
        with django_assert_num_queries(select=1):
            cached_json_object(cjo_label)
        with django_assert_num_queries():
            cached_json_object(cjo_label)
        with django_assert_num_queries(select=1):
            cached_json_object(cjo_label, force_clear=True)
        with django_assert_num_queries():
            cached_json_object(cjo_label)
