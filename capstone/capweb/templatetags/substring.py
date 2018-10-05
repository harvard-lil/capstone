from django import template

register = template.Library()

@register.simple_tag()
def substring(full_string, start_idx, end_idx, *args, **kwargs):
    if "total" in full_string:
        return "Total"
    return full_string[start_idx:end_idx]
