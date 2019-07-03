import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from rest_framework.templatetags.rest_framework import urlize_quoted_links


register = template.Library()

@register.filter()
def urlize_url_fields_only(text):
    """
        Split text into quoted urls, and other. Other text is escaped normally; quoted urls are passed through
        urlize_quoted_links(), which performs escaping.
    """
    pieces = re.split(r'("https?://\S+")', text.decode())
    return mark_safe(''.join(urlize_quoted_links(piece) if i % 2 else escape(piece) for i, piece in enumerate(pieces)))