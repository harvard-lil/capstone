# steps to run immediately after loading django
import os

from django.conf import settings
from django.core.mail import EmailMessage
from smtplib import SMTPException
from retry import retry


# patch email sending to retry on error, to work around sporadic connection issues
EmailMessage.send = retry((SMTPException, TimeoutError), tries=2, delay=1)(EmailMessage.send)

### django-vite settings ###

if os.environ.get("RUN_FRONTEND") == "1":
    # If we are running with fab run_frontend, use DJANGO_VITE_DEV_MODE to serve live JS from vite dev server
    setattr(settings, "DJANGO_VITE_DEV_MODE", True)
else:
    # If not running with fab run_frontend, use existing JS in static/dist
    setattr(settings, "DJANGO_VITE_STATIC_URL_PREFIX", "/static/dist/")

if settings.DEBUG:
    # In debug mode, use manifest in static/dist
    setattr(settings, "DJANGO_VITE_MANIFEST_PATH", os.path.join(settings.DJANGO_VITE_ASSETS_PATH, "manifest.json"))
else:
    # In production mode, use manifest in staticfiles/dist
    setattr(settings, "DJANGO_VITE_MANIFEST_PATH", os.path.join(settings.STATIC_ROOT, "dist/manifest.json"))
