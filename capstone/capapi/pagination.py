import json
import warnings
from base64 import b64decode, b64encode
from collections import OrderedDict
from django_elasticsearch_dsl_drf.versions import ELASTICSEARCH_GTE_6_0

from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination, _reverse_ordering, Cursor
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param

from capapi.resources import CachedCountQuerySet


class FTSPagination(CursorPagination):
    """
        Special paginator to deal with full text search. We know we are executing a full text search if the query
         has an ordering of ('fts_order',)
    """
    def paginate_queryset(self, queryset, request, view=None):
        """
            This method has to be copied and pasted from DRF, but only varies from super() in the parts that
            set and check self.FTS_ORDER
        """
        self.page_size = self.get_page_size(request)
        if not self.page_size:
            return None

        self.base_url = request.build_absolute_uri()
        self.ordering = self.get_ordering(request, queryset, view)

        self.FTS_ORDER = self.ordering == ('fts_order',)

        self.cursor = self.decode_cursor(request)
        if self.cursor is None:
            (offset, reverse, current_position) = (0, False, None)
        else:
            (offset, reverse, current_position) = self.cursor

        # Cursor pagination always enforces an ordering.
        if reverse:
            queryset = queryset.order_by(*_reverse_ordering(self.ordering))
        else:
            queryset = queryset.order_by(*self.ordering)

        # If we have a cursor with a fixed position then filter by that.
        if current_position is not None:
            order = 'case_text__metadata_id' if self.FTS_ORDER else self.ordering[0]
            is_reversed = order.startswith('-')
            order_attr = order.lstrip('-')

            # Test for: (cursor reversed) XOR (queryset reversed)
            if self.cursor.reverse != is_reversed:
                kwargs = {order_attr + '__lt': current_position}
            else:
                kwargs = {order_attr + '__gt': current_position}

            queryset = queryset.filter(**kwargs)

        # If we have an offset cursor then offset the entire page by that amount.
        # We also always fetch an extra item in order to determine if there is a
        # page following on from this one.
        results = list(queryset[offset:offset + self.page_size + 1])
        self.page = list(results[:self.page_size])

        # Determine the position of the final item following the page.
        if len(results) > len(self.page):
            has_following_position = True
            following_position = self._get_position_from_instance(results[-1], self.ordering)
        else:
            has_following_position = False
            following_position = None

        # If we have a reverse queryset, then the query ordering was in reverse
        # so we need to reverse the items again before returning them to the user.
        if reverse:
            self.page = list(reversed(self.page))

        if reverse:
            # Determine next and previous positions for reverse cursors.
            self.has_next = (current_position is not None) or (offset > 0)
            self.has_previous = has_following_position
            if self.has_next:
                self.next_position = current_position
            if self.has_previous:
                self.previous_position = following_position
        else:
            # Determine next and previous positions for forward cursors.
            self.has_next = has_following_position
            self.has_previous = (current_position is not None) or (offset > 0)
            if self.has_next:
                self.next_position = following_position
            if self.has_previous:
                self.previous_position = current_position

        # Display page controls in the browsable API if there is more
        # than one page.
        if (self.has_previous or self.has_next) and self.template is not None:
            self.display_page_controls = True

        return self.page

    def decode_cursor(self, request):
        """ Objects with FTS ordering come in with an fts_order value which is a float. We have to convert to int for the query. """
        cursor = super().decode_cursor(request)
        if cursor and self.FTS_ORDER:
            return Cursor(offset=cursor.offset, reverse=cursor.reverse, position=cursor.position.split('.', 1)[0])
        return cursor


class CapPagination(FTSPagination):
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
        TODO: This could potentially be contributed upstream instead of staying in CAP.
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
                return queryset.execute().to_dict().get('suggest')
            return queryset.execute_suggest().to_dict()

        # Check if we're using paginate queryset from `functional_suggest`
        # backend.
        if view.action == 'functional_suggest':
            return queryset

        self.resp = resp = self._paginate_queryset(queryset, request, view)
        self.facets = getattr(resp, 'aggregations', None)
        self.display_page_controls = self.has_next and self.template is not None
        return list(resp)

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
        if facets is None:
            facets = self.facets

        if facets is None:
            return None

        if hasattr(facets, '_d_'):
            return facets._d_

    def get_paginated_response_context(self, data):
        """Get paginated response data.

        :param data:
        :return:
        """
        __data = [
            ('count', self.count),
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

    def get_count(self, es_response):
        return es_response.hits.total


class ESCursorPagination(ESPaginatorMixin, CursorPagination):
    """
        Generic class for paginating django_elasticsearch_dsl_drf queries using search_after.
        TODO: This could potentially be contributed upstream instead of staying in CAP.
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
        self.count = self.get_count(resp)

        hits = resp.hits
        has_extra = len(hits) > self.page_size
        if has_extra:
            hits.pop()
        if self.reversed:
            hits.reverse()
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
        return self.encode_cursor({'p': list(self.resp.hits[-1].meta.sort)})

    def get_previous_link(self):
        if not self.has_previous:
            return None
        return self.encode_cursor({'p': list(self.resp.hits[0].meta.sort), 'r':1})

class CapESCursorPagination(ESCursorPagination):
    """
        CAP-specific customization of elasticsearch search_after pagination.
    """
    page_size_query_param = 'page_size'
    max_page_size = 100
    fallback_sort_field = "id"