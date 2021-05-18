from django.apps import AppConfig


class CapwebConfig(AppConfig):
    name = 'capweb'

    def ready(self):
        import config.post_django_setup  # noqa
