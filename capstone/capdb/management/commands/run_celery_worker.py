import shlex
import subprocess

from django.utils import autoreload
from django.core.management.base import BaseCommand

# Create a command to autoreload celery beat for elasticsearch indexing
def autoreload_celery(*args, **kwargs):
    celery_worker_cmd = "celery worker -A config.celery.app -c 1 -B --uid=nobody --gid=nogroup"
    print("Kill lingering celery worker...")
    subprocess.run(shlex.split(f'pkill -f "{celery_worker_cmd}"'))
    print("Start celery worker...")
    subprocess.run(shlex.split(celery_worker_cmd))

class Command(BaseCommand):
    help = 'Autoreload celery beat worker for elasticsearch indexing'

    def handle(self, *args, **options):
        autoreload.run_with_reloader(autoreload_celery)
