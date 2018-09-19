from django import template
from capapi import api_reverse

register = template.Library()

@register.simple_tag()
def api_url(url_name, *args, **kwargs):
    """ Like the {% url %} tag, but output includes the full domain. """
    return api_reverse(url_name, args=args, kwargs=kwargs)