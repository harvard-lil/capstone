import shlex
import subprocess

from django.utils import autoreload
from django.core.management.base import BaseCommand

# Create a command to autoreload celery beat for elasticsearch indexing
def autoreload_celery(*args, **kwargs):
    print("Restarting celery...")
    autoreload.raise_last_exception()
    kill_celery = "ps aux | grep bin/celery | awk '{print $2}' | xargs kill -9"
    subprocess.call(kill_celery, shell=True)
    start_celery = "celery worker -A config.celery.app -c 1 -B"
    subprocess.call(shlex.split(start_celery))

class Command(BaseCommand):
    help = 'Autoreload celery beat worker for elasticsearch indexing'

    def handle(self, *args, **options):
        self.stdout.write("Starting celery worker with autoreload...")
        autoreload.run_with_reloader(autoreload_celery, args=None, kwargs=None)
