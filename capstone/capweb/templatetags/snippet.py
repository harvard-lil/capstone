from django import template
from capdb.models import Snippet

register = template.Library()

@register.simple_tag()
def snippet(label):
    """
        Return contents of named Snippet. If Snippet is not found, return empty string.
    """
    try:
        return Snippet.objects.get(label=label).contents
    except Snippet.DoesNotExist:
        return ""
