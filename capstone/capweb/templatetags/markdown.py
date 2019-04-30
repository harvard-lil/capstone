from django import template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from capweb.helpers import render_markdown

register = template.Library()

"""
    This file provides a set of helpers to include markdown documents directly in templates. These are only necessary
    if you want to merge markdown with larger HTML templates. If you want an entire page in markdown, you can use the
    MarkdownView view instead.
"""

def get_markdown(context, template_path):
    key = 'markdown_%s' % template_path
    if key not in context:
        text = get_template(template_path).template.source
        context[key] = render_markdown(text)
    return context[key]

@register.simple_tag(takes_context=True)
def markdown(context, template_path):
    """ {% markdown 'terms-of-use.md' %} """
    return mark_safe(get_markdown(context, template_path)[0])

@register.simple_tag(takes_context=True)
def markdown_toc(context, template_path):
    """ {% markdown_toc 'terms-of-use.md' %} """
    return mark_safe(get_markdown(context, template_path)[1])

@register.simple_tag(takes_context=True)
def markdown_meta(context, template_path, key):
    """ {% markdown_meta 'terms-of-use.md' 'explainer' %} """
    return mark_safe(get_markdown(context, template_path)[2][key])

