from collections import OrderedDict
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from capapi.resources import CachedCountQuerySet


class CapPagination(CursorPagination):
    # This should be larger than the max number of records that share the same ordering field, such as decision_date,
    # but not too much larger to avoid allowing needlessly expensive queries.
    offset_cutoff = 10000

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