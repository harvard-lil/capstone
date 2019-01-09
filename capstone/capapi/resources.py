import hashlib
import json
from datetime import datetime
import logging
import zipfile
import tempfile
from wsgiref.util import FileWrapper
import wrapt

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connections
from django.db.models import QuerySet
from django.template.defaultfilters import slugify
from django.http import FileResponse
from django.test.utils import CaptureQueriesContext
from django_hosts import reverse as django_hosts_reverse

from capapi.tasks import cache_query_count
from capweb.helpers import reverse, statement_timeout, StatementTimeout

logger = logging.getLogger(__name__)


def create_zip_filename(case_list):
    ts = slugify(datetime.now().timestamp())
    if len(case_list) == 1:
        return case_list[0].slug + '-' + ts + '.zip'

    return '{0}_{1}_{2}.zip'.format(case_list[0].slug[:20], case_list[-1].slug[:20], ts)


def create_download_response(filename='', content=[]):
    # tmp file backed by RAM up to 10MB, then stored to disk
    tmp_file = tempfile.SpooledTemporaryFile(10 * 2 ** 20)
    with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in content:
            archive.writestr(item['slug'] + '.json', json.dumps(item))

    # Reset file pointer
    tmp_file.seek(0)

    response = FileResponse(FileWrapper(tmp_file), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


def send_new_signup_email(request, user):
    token_url = reverse('verify-user', kwargs={'user_id':user.pk, 'activation_nonce': user.get_activation_nonce()}, scheme="https")
    send_mail(
        'Caselaw Access Project: Verify your email address',
        "Please click here to verify your email address: \n\n%s \n\nIf you believe you have received this message in error, please ignore it." % token_url,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False, )
    logger.info("sent new_signup email for %s" % user.email)


def form_for_request(request, FormClass, *args, **kwargs):
    """ return FormClass loaded with request.POST data, if any """
    return FormClass(request.POST if request.method == 'POST' else None, *args, **kwargs)


class TrackingWrapper(wrapt.ObjectProxy):
    """
        Object wrapper that stores all accessed attributes of underlying object in _self_accessed_attrs. Example:

            user = CapUser.objects.get(pk=1)
            user = TrackingWrapper(user)
            print(user.id)
            assert user._self_accessed_attrs == {'id'}
    """
    def __init__(self, wrapped):
        super().__init__(wrapped)
        self._self_accessed_attrs = set()

    def __getattr__(self, item):
        self._self_accessed_attrs.add(item)
        return super().__getattr__(item)


class CachedCountQuerySet(QuerySet):
    """
        Queryset that caches counts based on generated SQL.
        Usage: queryset.__class__ = CachedCountQuerySet

        We take a few seconds to attempt to fetch the count live. If it does not return in time, we return None.
        We also cache a value of "IN_PROGRESS", and start a background job with cache_query_count.delay() to
        determine the real value.
    """
    def count(self):
        if self.query.is_empty():
            return 0

        cache_key = 'query-count:' + hashlib.md5(str(self.query).encode('utf8')).hexdigest()

        # return existing value if any
        value = cache.get(cache_key)
        if value == "IN_PROGRESS":
            return None
        elif value is not None:
            return value

        # cache new value
        conn = connections["capdb"]
        queries = None
        try:
            with statement_timeout(settings.LIVE_COUNT_TIME_LIMIT, "capdb"), CaptureQueriesContext(conn) as queries:
                value = super().count()
                # for testing:
                # conn.cursor().execute("SELECT pg_sleep(2);")
        except StatementTimeout:
            count_sql = queries.captured_queries[0]['sql']
            cache.set(cache_key, "IN_PROGRESS", 60*10)
            cache_query_count.delay(count_sql, cache_key)
            return None
        else:
            cache.set(cache_key, value, settings.CACHED_COUNT_TIMEOUT)
            return value


class CachedCountDefaultQuerySet(CachedCountQuerySet):
    """ Like CachedCountQuerySet, but returns default_count if counting times out. """
    default_count = 1000000
    def count(self):
        return super().count() or self.default_count


def api_reverse(viewname, args=None, kwargs=None, request=None, format=None, **extra):
    """
        Same as `django.urls.reverse`, but uses api_urls.py for routing, and includes full domain name.
    """
    if format is not None:
        kwargs = kwargs or {}
        kwargs['format'] = format
    return django_hosts_reverse(viewname, args=args, kwargs=kwargs, host='api', scheme='http' if settings.DEBUG else 'https', **extra)
