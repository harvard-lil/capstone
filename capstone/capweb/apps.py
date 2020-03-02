from django.apps import AppConfig


class CapwebConfig(AppConfig):
    name = 'capweb'

    def ready(self):
        # Speed optimization hack for Django 2.2 -- these settings are deprecated, and the way Django checks for deprecation adds
        # stack inspection to every request. Undo the deprecation check.
        from django.conf import settings, LazySettings
        LazySettings.DEFAULT_CONTENT_TYPE = settings.DEFAULT_CONTENT_TYPE
        LazySettings.FILE_CHARSET = settings.FILE_CHARSET
