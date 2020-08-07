import json
import warnings
from base64 import b64decode, b64encode
from collections import OrderedDict

from django.conf import settings
from django_elasticsearch_dsl_drf.versions import ELASTICSEARCH_GTE_6_0

from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param

from capapi.resources import CachedCountQuerySet


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

    def _paginate_queryset(self, queryset, request, view):
        """
            subclasses should:
             - set self.has_next
             - set self.has_previous
             - set self.count
             - return elasticsearch Response object
        """
        raise NotImplementedError

    def get_facets(self, facets=None):
        """Get facets.

        :param facets:
        :return:
        """
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

    @staticmethod
    def reverse_sort(queryset):
        new_sort = []
        for item in queryset._sort:
            if type(item) == str:
                item = {item: {"order": "asc" if item == "_score" else "desc"}}
            elif type(item) == dict  and item:
                k = next(iter(item))
                v = dict(item[k])
                v["order"] = "desc" if v.get("order", "desc" if k == "_score" else "asc") == "asc" else "desc"
                item = {k: v}
            else:
                raise TypeError("Unrecognized sort order: %s" % item)
            new_sort.append(item)
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
            queryset = self.reverse_sort(queryset)
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