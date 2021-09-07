from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured


def settings(request):
    """
    Adds the settings specified in settings.TEMPLATE_VISIBLE_SETTINGS to the request context.
    From https://github.com/mfogel/django-settings-context-processor/blob/master/settings_context_processor/context_processors.py
    """
    new_settings = {}
    for attr in getattr(django_settings, "TEMPLATE_VISIBLE_SETTINGS", ()):
        try:
            new_settings[attr] = getattr(django_settings, attr)
        except AttributeError:
            m = f"TEMPLATE_VISIBLE_SETTINGS: '{attr}' does not exist"
            raise ImproperlyConfigured(m)
    return new_settings
