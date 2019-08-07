from django import template
from django.utils.safestring import mark_safe

from capdb.models import Snippet

register = template.Library()

@register.simple_tag()
def snippet(label, default=""):
    """
        Return contents of named Snippet. If Snippet is not found, return default.
    """
    try:
        return mark_safe(Snippet.objects.get(label=label).contents)
    except Snippet.DoesNotExist:
        return mark_safe(default)
