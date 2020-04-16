"""
WSGI config for capstone project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# patch email sending to retry on error, to work around sporadic connection issues
from django.core.mail import EmailMessage
from smtplib import SMTPException
from time import sleep
_orig_send = EmailMessage.send
def retrying_send(message, *args, **kwargs):
    try:
        return _orig_send(message, *args, **kwargs)
    except (SMTPException, TimeoutError):
        sleep(1)
        return _orig_send(message, *args, **kwargs)
EmailMessage.send = retrying_send

application = get_wsgi_application()
