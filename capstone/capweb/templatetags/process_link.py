from django import template

from capweb.helpers import reverse
from django.urls.resolvers import NoReverseMatch

register = template.Library()

@register.simple_tag()
def process_link(link, *args, **kwargs):
    """

    :param link: Either a link or a route
    :return: Either the original link, or the link made from the reversed route
    """
    if link and (not link.startswith("http")):
        # if it doesn't start with http, see if it's a django path. if not: 🤷‍
        try:
            return reverse(link)
        except NoReverseMatch:
            pass
    else:
        return link

