# set up Django
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print("WARNING: Can't configure Django -- tasks depending on Django will fail:\n%s" % e)

from django.contrib.auth.models import User
from fabric.api import run, local
from fabric.decorators import task

# from process_ingested_xml import fill_case_page_join_table
from scripts import set_up_postgres, ingest_tt_data, ingest_files, data_migrations


@task(alias='run')
def run_django():
    local("python manage.py runserver")

@task
def ingest_volumes():
    ingest_files.ingest_volumes()

@task
def ingest_metadata():
    ingest_tt_data.ingest(False)

@task
def sync_metadata():
    ingest_tt_data.ingest(True)

@task
def run_pending_migrations():
    data_migrations.run_pending_migrations()

@task
def update_postgres_env():
    set_up_postgres.update_postgres_env()

@task
def init_db():
    """
        Set up new dev database.
    """
    local("python manage.py migrate")
    print("Creating DEV admin user:")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')

    update_postgres_env()
