import re

from django import template
from django.utils.html import escape, urlize
from django.utils.safestring import mark_safe
from django.utils.encoding import force_str

register = template.Library()

@register.filter()
def urlize_url_fields_only(text):
    """
        Split text into quoted urls, and other. Other text is escaped normally; quoted urls are passed through
        urlize(), which performs escaping.
    """
    pieces = re.split(r'("https?://\S+")', force_str(text))
    return mark_safe(''.join(urlize(piece) if i % 2 else escape(piece) for i, piece in enumerate(pieces)))
