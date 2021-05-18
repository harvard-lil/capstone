from django import template
from django.utils.safestring import mark_safe
from markdown import Markdown as md
from django.template import Template, Context

register = template.Library()

@register.simple_tag()
def md_chunk(md_chunk, *args, **kwargs):
    template = Template(md_chunk)
    context = Context()

    html_content = md().convert(template.render(context))
    return mark_safe(html_content)