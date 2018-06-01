import hashlib
from rest_framework.pagination import LimitOffsetPagination

from django.conf import settings
from django.core.cache import caches


def CachedCountQueryset(queryset, timeout=60*60, cache_name='default'):
    """
        Return copy of queryset with queryset.count() wrapped to cache result for `timeout` seconds.
    """
    cache = caches[cache_name]
    queryset = queryset._chain()
    real_count = queryset.count

    def count(queryset):
        cache_key = 'query-count:' + hashlib.md5(str(queryset.query).encode('utf8')).hexdigest()

        # return existing value, if any
        value = cache.get(cache_key)
        if value is not None:
            return value

        # cache new value
        value = real_count()
        cache.set(cache_key, value, timeout)
        return value

    queryset.count = count.__get__(queryset, type(queryset))
    return queryset


class CachedCountLimitOffsetPagination(LimitOffsetPagination):
    def paginate_queryset(self, queryset, *args, **kwargs):
        if hasattr(queryset, 'count'):
            queryset = CachedCountQueryset(queryset, settings.API_COUNT_CACHE_TIMEOUT)
        return super().paginate_queryset(queryset, *args, **kwargs)