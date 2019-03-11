from collections import OrderedDict
from rest_framework.pagination import CursorPagination, _reverse_ordering, Cursor
from rest_framework.response import Response

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