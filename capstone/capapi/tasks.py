from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from capapi.models import SiteLimits, CapUser


@shared_task
def daily_site_limit_reset_and_report():
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