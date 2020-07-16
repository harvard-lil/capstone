from django import template


register = template.Library()


@register.filter()
def redact(text, case):
    return case.redact_obj(text)


@register.filter()
def elide(text, case):
    return case.elide_obj(text)