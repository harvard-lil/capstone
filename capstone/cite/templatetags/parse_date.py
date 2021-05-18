from django import template

from scripts.process_metadata import parse_decision_date

register = template.Library()


@register.filter()
def parse_date(date_string):
    return parse_decision_date(date_string)
