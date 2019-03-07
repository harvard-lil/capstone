from re import findall

from django import template
from django.utils.html import escape
import re


from rest_framework.templatetags.rest_framework import urlize_quoted_links

register = template.Library()

@register.filter()
def urlize_url_fields_only(text):
    ret = re.sub(
        '&quot;(http:.*)?(&quot;)',
        lambda url_match: urlize_quoted_links(url_match.group(1)),
        escape(text.decode()))
    return ret
