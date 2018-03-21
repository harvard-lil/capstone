from collections import OrderedDict

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.utils.urls import replace_query_param
from rest_framework.response import Response


class CountlessPagination(LimitOffsetPagination):
    """
    This is a custom paginator that's limit/offset based, but
    does not include count, and so only shows next/previous
    buttons in browsing mode
    """
    template = 'rest_framework/pagination/previous_and_next.html'

    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        if self.limit is None:
            return None
        self.offset = self.get_offset(request)
        self.request = request
        self.display_page_controls = True
        return list(queryset[self.offset:self.offset + self.limit])

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', None),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))

    def get_next_link(self):
        url = self.request.build_absolute_uri()
        url = replace_query_param(url, self.limit_query_param, self.limit)

        offset = self.offset + self.limit
        return replace_query_param(url, self.offset_query_param, offset)

    def get_html_context(self):
        return {
            'previous_url': self.get_previous_link(),
            'next_url': self.get_next_link()
        }
