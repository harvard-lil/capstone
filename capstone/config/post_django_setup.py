# steps to run immediately after loading django

from django.core.mail import EmailMessage
from smtplib import SMTPException
from retry import retry


# patch email sending to retry on error, to work around sporadic connection issues
EmailMessage.send = retry((SMTPException, TimeoutError), tries=2, delay=1)(EmailMessage.send)
