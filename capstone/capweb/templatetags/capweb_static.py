from django import template
from django_hosts import reverse
from django.conf import settings

register = template.Library()

@register.simple_tag()
def capweb_static(path):
    host = reverse("home", args={}, kwargs={}, host="default", scheme='http' if settings.DEBUG else 'https')[:-1]
    return "{}{}{}".format(host, settings.STATIC_URL, path)
