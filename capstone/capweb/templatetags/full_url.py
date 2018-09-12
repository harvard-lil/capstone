from django import template
from rest_framework.reverse import reverse

register = template.Library()

@register.simple_tag(takes_context=True)
def full_url(context, url_name, *args, **kwargs):
    """ Like the {% url %} tag, but output includes the full domain. """
    return reverse(url_name, args=args, kwargs=kwargs, request=context.request)