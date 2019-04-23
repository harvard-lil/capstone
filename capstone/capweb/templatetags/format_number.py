from django import template

register = template.Library()


@register.filter
def format_number(number, *args, **kwargs):
    """ Like the {% url %} tag, but output includes the full domain. """
    num_formatted = "{:,}".format(number)
    return num_formatted
