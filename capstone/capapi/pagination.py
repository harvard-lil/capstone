import hashlib
from rest_framework.pagination import LimitOffsetPagination

from django.conf import settings

from capapi.resources import cache_func


def CachedCountQueryset(queryset, timeout=60*60, cache_name='default'):
    """
        Return copy of queryset with queryset.count() wrapped to cache result for `timeout` seconds.
    """
    queryset = queryset._chain()
    real_count = queryset.count

    @cache_func(
        key=lambda queryset:'query-count:' + hashlib.md5(str(queryset.query).encode('utf8')).hexdigest(),
        timeout=timeout,
        cache_name=cache_name,
    )
    def count(queryset):
        return real_count()

    queryset.count = count.__get__(queryset, type(queryset))
    return queryset


class CachedCountLimitOffsetPagination(LimitOffsetPagination):
    max_limit = 100

    def paginate_queryset(self, queryset, *args, **kwargs):
        if hasattr(queryset, 'count'):
            queryset = CachedCountQueryset(queryset, settings.API_COUNT_CACHE_TIMEOUT)
        return super().paginate_queryset(queryset, *args, **kwargs)
