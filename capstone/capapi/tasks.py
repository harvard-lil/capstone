from datetime import timedelta
import requests

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connections
from django.utils import timezone

from capweb.helpers import statement_timeout, StatementTimeout


@shared_task
def daily_site_limit_reset_and_report():
    from capapi.models import SiteLimits, CapUser  # import here to avoid circular import

    site_limits = SiteLimits.get()

    # send admin email
    users_created_today = CapUser.objects.filter(date_joined__gte=timezone.now()-timedelta(days=1)).values_list('email', flat=True)
    send_mail(
        'CAP daily usage: %s registered users, %s blacklisted downloads' % (site_limits.daily_signups, site_limits.daily_downloads),
        """
Blacklist cases downloaded: %s
User signups: %s
User emails:

%s
        """ % (site_limits.daily_downloads, site_limits.daily_signups, "\n".join(users_created_today)),
        settings.DEFAULT_FROM_EMAIL,
        [settings.DEFAULT_FROM_EMAIL],
        fail_silently=False,
    )

    # log status
    print("CAP daily usage report: created %s new users, %s blacklisted cases downloaded" % (site_limits.daily_signups, site_limits.daily_downloads))

    # reset limits
    SiteLimits.reset()

    # notify external service
    try:
        url = settings.HEALTHCHECK_URL["%s.daily_site_limit_reset_and_report" % __name__]
        if url:
            r = requests.get(url)
            if r.status_code != requests.codes.ok:
                print("CAP daily usage report was unable to notify healthcheck service.")
    except KeyError:
        pass

@shared_task
def cache_query_count(sql, cache_key):
    """ Cache the result of a count() sql query, because it didn't return quickly enough the first time. """
    try:
        with connections["capdb"].cursor() as cursor, statement_timeout(settings.TASK_COUNT_TIME_LIMIT, "capdb"):
            cursor.execute(sql)
            result = cursor.fetchone()
            cache.set(cache_key, result[0], settings.CACHED_COUNT_TIMEOUT)
    except StatementTimeout:
        pass  # this count takes too long to calculate -- move on
