from re import findall

from django import template
from django.utils.html import escape

from rest_framework.templatetags.rest_framework import urlize_quoted_links

register = template.Library()

@register.filter()
def urlize_url_fields_only(text):
    ret = escape(text.decode())
    for url in findall('"url": "(http[^"]+)"', text.decode()):
        ret = ret.replace(url, urlize_quoted_links(url))
    return ret
