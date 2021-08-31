import json
import warnings
from base64 import b64decode, b64encode
from collections import OrderedDict
from datetime import datetime

from django.conf import settings
from django_elasticsearch_dsl_drf.versions import ELASTICSEARCH_GTE_6_0
from elasticsearch import TransportError

from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework import serializers

from capapi.resources import CachedCountQuerySet


## helpers ##

def _reverse_elastic_sort(current_sort, valid_field_names):
    """
        Reverse each item in current_sort, which is an elasticsearch sort order list.
        (See https://www.elastic.co/guide/en/elasticsearch/reference/current/sort-search-results.html for format.)
        This currently strips all sorting options except for "order". Otherwise we'd need an allowlist or signature on the cursor, since it's user-submitted data.

        Example: 'asc' becomes 'desc', 'desc' becomes 'asc', plain 'id' becomes {'id': {'order': 'desc'}}:
        >>> assert _reverse_elastic_sort([{'_score': {'order': 'desc'}}, {'date': {'order': 'asc'}}, 'id'], ['_score', 'date', 'id']) == \
                [{'_score': {'order': 'asc'}}, {'date': {'order': 'desc'}}, {'id': {'order': 'desc'}}]

        valid_field_names makes sure that invalid fields aren't passed in:
        >>> assert _reverse_elastic_sort([{'date': {'order': 'asc'}}, {'bad': {'order': 'asc'}}], ['date']) == \
                [{'date': {'order': 'desc'}}]
    """
    new_sort = []
    for item in current_sort:
        if isinstance(item, str):
            # inflate str-only fields like 'id' to dicts like {'id': {'order': 'asc'}}
            item = {item: {"order": "asc"}}
        try:
            # get 'id' from {'id': {'order': 'asc'}}
            field_name = next(iter(item))
            # this would only happen if cursor was manually edited
            if field_name not in valid_field_names:
                continue
            # update order
            new_order = "desc" if item[field_name]["order"] == "asc" else "asc"
            item = {field_name: {"order": new_order}}
        except Exception:
            raise TypeError("Unrecognized sort order: %s" % item)
        new_sort.append(item)
    return new_sort


## paginators ##

class CapPagination(CursorPagination):
    # This should be larger than the max number of records that share the same ordering field, such as decision_date,
    # but not too much larger to avoid allowing needlessly expensive queries.
    offset_cutoff = 10000

    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, *args, **kwargs):
        # cache result counts to save on expensive count queries
        if hasattr(queryset, 'count'):
            queryset = queryset._chain()
            queryset.__class__ = CachedCountQuerySet

        # copied from LimitOffsetPagination to support 'count' field
        self.count = self.get_count(queryset)

        return super().paginate_queryset(queryset, *args, **kwargs)

    def get_ordering(self, request, queryset, view):
        """ Derive ordering from queryset, rather than hardcoding as CursorPagination does. """
        ordering = queryset.query.order_by or queryset.model._meta.ordering

        assert ordering and isinstance(ordering, (str, list, tuple)), (
            'Invalid ordering. Expected string or tuple, but got %s' % (ordering,)
        )

        return ordering

    def get_paginated_response(self, data):
        # copied from LimitOffsetPagination to support 'count' field
        return Response(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))

    def get_count(self, queryset):
        # copied from LimitOffsetPagination to support 'count' field
        try:
            return queryset.count()
        except (AttributeError, TypeError):
            return len(queryset)


class SmallCapPagination(CapPagination):
    page_size = 10
    max_page_size = 10


class ESPaginatorMixin:
    """
        Parent class for pagination functions common to django_elasticsearch_dsl_drf paginators.
    """
    template = None
    facets = None
    count = None

    def paginate_queryset(self, queryset, request, view=None):
        try:
            # Check if there are suggest queries in the queryset,
            # ``execute_suggest`` method shall be called, instead of the
            # ``execute`` method and results shall be returned back immediately.
            # Placing this code at the very start of ``paginate_queryset`` method
            # saves us unnecessary queries.
            is_suggest = getattr(queryset, '_suggest', False)
            if is_suggest:
                if ELASTICSEARCH_GTE_6_0:
                    return queryset.execute().get('suggest')
                return queryset.execute_suggest()

            # Check if we're using paginate queryset from `functional_suggest`
            # backend.
            if view.action == 'functional_suggest':
                return queryset

            self.resp = resp = self._paginate_queryset(queryset, request, view)
            self.facets = resp.get('aggregations', None)
            self.display_page_controls = self.has_next and self.template is not None
            return resp['hits']['hits']
        except TransportError as e:
            if e.error == 'search_phase_execution_exception':
                raise serializers.ValidationError({'error': ['Invalid query parameters']})
            raise

    def _paginate_queryset(self, queryset, request, view):
        """
            subclasses should:
             - set self.has_next
             - set self.has_previous
             - set self.count
             - return elasticsearch Response object
        """
        raise NotImplementedError

    def parse_bucket_key(self, blob):
        """Generate and parse blob key.

        :param string:
        :return:
        """
        if 'key_as_string' in blob:
            try:
                return datetime.strptime(blob['key_as_string'], '%Y-%m-%dT%H:%M:%S.%fZ').year
            except ValueError:
                return blob['key']

        return blob['key']

    def get_facets(self, facets=None):
        """Get facets. ONLY return up to max depth two layers to avoid infinite recursion

        :param facets:
        :return:
        """
        newfacetdict = {}

        if not self.facets:
            return self.facets

        for facetkey in self.facets:
            newfacetdict[facetkey] = {}

            keys = facetkey.split(',')

            for bucket in self.facets[facetkey]['buckets']:             
                value = bucket['doc_count']
                if len(keys) == 2 and keys[1] in bucket and type(bucket[keys[1]]) == dict:
                    value = {self.parse_bucket_key(blob):blob['doc_count'] for blob in bucket[keys[1]]['buckets']}

                newfacetdict[facetkey][self.parse_bucket_key(bucket)] = value

        self.facets = newfacetdict

        return self.facets if facets is None else facets

    def get_paginated_response_context(self, data):
        """Get paginated response data.

        :param data:
        :return:
        """
        __data = [
            ('count', self.count['value']),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
        ]
        __facets = self.get_facets()
        if __facets is not None:
            __data.append(
                ('facets', __facets),
            )
        __data.append(
            ('results', data),
        )
        return __data

    def get_paginated_response(self, data):
        """Get paginated response.

        :param data:
        :return:
        """
        return Response(OrderedDict(self.get_paginated_response_context(data)))


class ESCursorPagination(ESPaginatorMixin, CursorPagination):
    """
        Generic class for paginating django_elasticsearch_dsl_drf queries using search_after.
    """
    fallback_sort_field = "_id"

    def __init__(self, *args, **kwargs):
        if self.fallback_sort_field == "_id":
            warnings.warn(
                "fallback_sort_field of '_id' is inefficient. Consider changing it in a subclass. "
                "See https://www.elastic.co/guide/en/elasticsearch/reference/current/search-request-search-after.html")
        super(ESCursorPagination, self).__init__(*args, **kwargs)

    @classmethod
    def reverse_sort(cls, queryset, view):
        """
            Reverse each item in queryset._sort, so we get the same results in the opposite order.
        """
        valid_field_names = list(view.ordering_fields.values()) + [cls.fallback_sort_field]
        new_sort = _reverse_elastic_sort(queryset._sort, valid_field_names)
        return queryset.sort(*new_sort)

    def _paginate_queryset(self, queryset, request, view):
        # read query parameters
        self.page_size = self.get_page_size(request)
        if not self.page_size:
            return None
        self.base_url = request.build_absolute_uri()
        self.cursor = self.decode_cursor(request)
        self.reversed = self.cursor['r']
        self.search_after = self.cursor['p']

        # ensure sort order includes fallback_sort_field
        if not any(k == self.fallback_sort_field or self.fallback_sort_field in k.keys() for k in queryset._sort):
            queryset = queryset.sort(*(queryset._sort + [self.fallback_sort_field]))
        if self.reversed:
            queryset = self.reverse_sort(queryset, view)
        if self.search_after:
            queryset = queryset.extra(search_after=self.search_after)


        resp = queryset[:self.page_size+1].execute()
        hits = resp['hits']
        self.count = hits['total']

        has_extra = len(hits['hits']) > self.page_size
        if has_extra:
            hits['hits'].pop()
        if self.reversed:
            hits['hits'].reverse()
            self.has_next = True
            self.has_previous = has_extra
        else:
            self.has_next = has_extra
            self.has_previous = bool(self.search_after)

        return resp

    def decode_cursor(self, request):
        """
        Given a request with a cursor, return a search_after list.
        """
        # Determine if we have a cursor, and if so then decode it.
        encoded = request.query_params.get(self.cursor_query_param)
        if encoded is None:
            return {'p': [], 'r': False}
        try:
            querystring = b64decode(encoded.encode('ascii')).decode('utf8')
            cursor = json.loads(querystring)
            if not type(cursor['p']) == list or any(type(i) not in (str, int, float) for i in cursor['p']):
                raise TypeError
            cursor['r'] = 'r' in cursor
        except (TypeError, ValueError):
            raise NotFound(self.invalid_cursor_message)
        return cursor

    def encode_cursor(self, cursor):
        """
        Given a search_after list, return an url with encoded cursor.
        """
        querystring = json.dumps(cursor)
        encoded = b64encode(querystring.encode('utf8')).decode('ascii')
        return replace_query_param(self.base_url, self.cursor_query_param, encoded)

    def get_next_link(self):
        if not self.has_next:
            return None
        return self.encode_cursor({'p': self.resp['hits']['hits'][-1]['sort']})

    def get_previous_link(self):
        if not self.has_previous:
            return None
        return self.encode_cursor({'p': self.resp['hits']['hits'][0]['sort'], 'r':1})


class CapESCursorPagination(ESCursorPagination):
    """
        CAP-specific customization of elasticsearch search_after pagination.
    """
    page_size_query_param = 'page_size'
    max_page_size = settings.MAX_PAGE_SIZE
    fallback_sort_field = "id"

    def decode_cursor(self, request):
        """Don't allow use of cursor with random ordering, because we can't provide consistent pagination."""
        if request.query_params.get(self.cursor_query_param) and request.query_params.get('ordering') == 'random':
            raise serializers.ValidationError({'cursor': ['Pagination is not currently supported with random ordering. For a larger random sample, consider increasing page_size.']})
        return super().decode_cursor(request)
