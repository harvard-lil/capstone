import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_contact(data):
    subject = data.get('subject')
    message = data.get('message')
    sender = data.get('sender')
    recipient_list = [settings.EMAIL_ADDRESS]
    send_mail(subject, message, sender, recipient_list, fail_silently=False)

    logger.info("%s sent contact email" % sender)
