# steps to run immediately after loading django

from django.conf import settings, LazySettings
from django.core.mail import EmailMessage
from smtplib import SMTPException
from retry import retry


# Speed optimization hack for Django 2.2 -- these settings are deprecated, and the way Django checks for deprecation adds
# stack inspection to every request. Undo the deprecation check.
LazySettings.DEFAULT_CONTENT_TYPE = settings.DEFAULT_CONTENT_TYPE
LazySettings.FILE_CHARSET = settings.FILE_CHARSET


# patch email sending to retry on error, to work around sporadic connection issues
EmailMessage.send = retry((SMTPException, TimeoutError), tries=2, delay=1)(EmailMessage.send)
