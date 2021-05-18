from django import template

register = template.Library()

# h/t https://simpleisbetterthancomplex.com/snippets/startswith/
@register.filter('startswith')
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False
