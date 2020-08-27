import hashlib
import wrapt

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connections
from django.db.models import QuerySet
from django.utils.text import slugify
from django.test.utils import CaptureQueriesContext
from django.utils.functional import SimpleLazyObject
from django_hosts import reverse as django_hosts_reverse

from capapi.tasks import cache_query_count
from capweb.helpers import reverse, statement_timeout, StatementTimeout
from config.logging import logger

# To get characters in valid reporters:
#   ''.join(set(c for s in list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys()) for c in s if not re.match(r'[a-zA-Z0-9]', c)))
# To get max reporter length:
#   max(len(i) for i in list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys()))
cite_extracting_regex = (
    r"\b([1-9]\d*(?: Suppl\.| 1/2)?) +"             # volume number, with optional Suppl. or 1/2
    r"([a-zA-Z][ 0-9a-zA-Z.,\-'&()]{0,32}?) +"      # reporter string, including all characters found in reporters_db
    r"([1-9]\d*)\b(?! Cir.)"                        # page number, which cannot be followed by " Cir." to avoid matching reporters like "La.App. 5 Cir." as La.App. page 5
)


def send_new_signup_email(request, user):
    token_url = reverse('verify-user', kwargs={'user_id':user.pk, 'activation_nonce': user.get_activation_nonce()}, scheme="https")
    send_mail(
        'Caselaw Access Project: Verify your email address',
        "Please click here to verify your email address: \n\n%s \n\nIf you received this message in error, please ignore it." % token_url,
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


def wrap_user(request, user):
    """
        Prepare a user object for use in our stack. This does two things:
        - wrap the user object in TrackingWrapper, so we can tell what attributes are accessed
          by checking user._self_accessed_attrs
        - set user.ip_address, so we can check the user's IP address
        This intentionally re-wraps the user object if called twice, so the tracking is reset.
    """
    def inner_wrap_user():
        wrapped_user = TrackingWrapper(user)
        wrapped_user.ip_address = request.META.get('HTTP_CF_CONNECTING_IP')
        return wrapped_user
    return SimpleLazyObject(inner_wrap_user)


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
    scheme = 'http' if settings.DEBUG else 'https'
    out = django_hosts_reverse(viewname, args=args, kwargs=kwargs, host='api', scheme=scheme, **extra)

    # for debugging, replace 'http://api.case.test:8000' with value of settings.API_HOST_OVERRIDE
    if settings.API_HOST_OVERRIDE:
        return out.replace('%s://%s.%s' % (scheme, settings.HOSTS['api']['subdomain'], settings.PARENT_HOST), settings.API_HOST_OVERRIDE)

    return out


def apply_replacements(item, replacements, prefix="[ ", suffix=" ]"):
    """ filters out terms in 'item' with the {'original_text': and 'replacement_text' }
    >>> apply_replacements("Hello, what's your name?", (('name', 'game'), ('Hello', 'Wow')))
    "[ Wow ], what's your [ game ]?"

    >>> apply_replacements({"test": "Hello, what's your name?" }, (('name', 'game'), ('Hello', 'Wow')))
    {'test': "[ Wow ], what's your [ game ]?"}
    """

    if not replacements:
        return item
    replacements = list(replacements)

    if isinstance(item, str):
        for replacement in replacements:
            item = item.replace(replacement[0], prefix + replacement[1] + suffix)
    elif isinstance(item, list):
        item = [apply_replacements(inner_item, replacements) for inner_item in item]
    elif isinstance(item, dict):
        item = {name: apply_replacements(inner_item, replacements) for (name, inner_item) in item.items()}
    elif not item:
        return item
    else:
        raise Exception("Unexpected redaction format")
    return item


def link_to_cites(case_html, cites):
    """ links previously matched cites in frontend view
    >>> link_to_cites("Town of Dayton v. Town of Rutland, 84 Ill. 279, Rutland v. Dayton, 60 Ill. 58", [{'cite': '84 Ill. 279'}, {'cite': '60 Ill. 58'}])
    "Town of Dayton v. Town of Rutland, <a href='http://cite.case.test:8000/ill/84/279/'>84 Ill. 279</a>, Rutland v. Dayton, <a href='http://cite.case.test:8000/ill/60/58/'>60 Ill. 58</a>"
    """
    from capdb.models import Citation
    for cite in cites:
        vol_num, reporter, page_num = Citation.parse_cite(cite['cite'])
        if not reporter:
            continue
        cite_link = "<a href='%s'>%s</a>" % (reverse('citation', host='cite', args=[slugify(reporter), slugify(vol_num), page_num]), cite['cite'])
        case_html = case_html.replace(cite['cite'], cite_link)

    return case_html
