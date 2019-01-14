from django import template
from capdb.models import Snippet

register = template.Library()

@register.simple_tag()
def snippet(label):
    return Snippet.objects.get(label=label).contents
