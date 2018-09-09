from rest_framework.pagination import LimitOffsetPagination

from capapi.resources import CachedCountQuerySet


class CachedCountLimitOffsetPagination(LimitOffsetPagination):
    max_limit = 100

    def paginate_queryset(self, queryset, *args, **kwargs):
        if hasattr(queryset, 'count'):
            queryset = queryset._chain()
            queryset.__class__ = CachedCountQuerySet
        return super().paginate_queryset(queryset, *args, **kwargs)
