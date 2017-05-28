# quick and dirty registration of all models in admin
# via https://stackoverflow.com/a/31184258/307769

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

app_models = apps.get_app_config('tracking_tool').get_models()
for model in app_models:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass