# via http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# when creating app, include any files with tasks outside of 'tasks.py', as they won't be found by autodiscover_tasks()
app = Celery('config', include=[
    'scripts.count_chars',
    'scripts.ingest_by_manifest',
    'scripts.validate_private_volumes',
    'scripts.compress_volumes',
    'scripts.ice_volumes',
    'scripts.export',
    'scripts.ngrams',
    'scripts.update_snippets',
    'scripts.refactor_xml',
])

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# configure celery_resource_limits
from django.conf import settings
app.conf.resource_limits = settings.CELERY_RESOURCE_LIMITS

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

