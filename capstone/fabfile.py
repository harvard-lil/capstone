# set up Django
import glob
import os
import django
import zipfile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print("WARNING: Can't configure Django -- tasks depending on Django will fail:\n%s" % e)

from django.conf import settings
from django.contrib.auth.models import User
from fabric.api import local
from fabric.decorators import task

from capapi import resources
from capdb.models import Jurisdiction, CaseMetadata
# from process_ingested_xml import fill_case_page_join_table
from scripts import set_up_postgres, ingest_tt_data, ingest_files, data_migrations, ingest_by_manifest


@task(alias='run')
def run_django():
    local("python manage.py runserver")

@task
def test():
    """ Run tests with coverage report. """
    local("pytest --fail-on-template-vars --cov --cov-report=")

@task
def recent_sync_with_s3():
    ingest_by_manifest.sync_recent_data()

@task
def total_sync_with_s3():
    ingest_by_manifest.complete_data_sync()

@task
def ingest_volumes():
    ingest_files.ingest_volumes()

@task
def update_case_metadata():
    ingest_files.update_case_metadata()

@task
def ingest_jurisdiction():
    ingest_tt_data.populate_jurisdiction()

@task
def ingest_metadata():
    ingest_tt_data.populate_jurisdiction()
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
    migrate()

    print("Creating DEV admin user:")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')

    update_postgres_env()

@task
def migrate():
    """
        Migrate all dbs at once
    """
    local("python manage.py migrate --database=default")
    local("python manage.py migrate --database=capapi")
    if settings.USE_TEST_TRACKING_TOOL_DB:
        local("python manage.py migrate --database=tracking_tool")

@task
def load_test_data():
    if settings.USE_TEST_TRACKING_TOOL_DB:
        local("python manage.py loaddata --database=tracking_tool test_data/tracking_tool.json")
    ingest_volumes()
    ingest_metadata()
    update_case_metadata()

@task
def write_tracking_tool_fixtures(*barcodes):
    """
        Write out subset of tracking_tool data needed for given list of barcodes.
        This assumes DATABASES['tracking_tool'] is configured to point to real tracking tool db.
        Output is stored in test_data/tracking_tool.json.
        By default, uses barcodes from folders in test_data/from_vendor.
        User details are anonymized.
    """
    from django.core import serializers
    from tracking_tool.models import Volumes, Reporters, BookRequests, Pstep, Eventloggers, Hollis, Users

    if not barcodes:
        barcodes = [os.path.basename(d).split('_')[0] for d in glob.glob(os.path.join(settings.BASE_DIR, 'test_data/from_vendor/*_redacted'))]

    to_serialize = set()
    user_ids = set()

    for barcode in barcodes:
        print("Writing data for", barcode)
        volume = Volumes.objects.get(bar_code=barcode)
        to_serialize.add(volume)

        user_ids.add(volume.created_by)

        reporter = Reporters.objects.get(id=volume.reporter_id)
        to_serialize.add(reporter)

        to_serialize.update(Hollis.objects.filter(reporter_id=reporter.id))

        request = BookRequests.objects.get(id=volume.request_id)
        request.from_field = request.recipients = 'example@example.com'
        to_serialize.add(request)

        for event in Eventloggers.objects.filter(bar_code=volume.bar_code):
            if not event.updated_at:
                event.updated_at = event.created_at
            to_serialize.add(event)
            user_ids.add(event.created_by)
            if event.pstep_id:
                pstep = Pstep.objects.get(step_id=event.pstep_id)
                to_serialize.add(pstep)

    for user in Users.objects.filter(id__in=user_ids):
        user.email = "example@example.com"
        user.password = 'password'
        user.remember_token = ''
        to_serialize.add(user)

    serializer = serializers.get_serializer("json")()
    with open(os.path.join(settings.BASE_DIR, "test_data/tracking_tool.json"), "w") as out:
        serializer.serialize(to_serialize, stream=out, indent=2)


@task
def zip_jurisdiction(jurname, zip_filename=None):
    """
    Write a zipped directory of all case xml files in a given jurisdiction.
    The uncompressed output's structure looks like: jurisdiction/reporter_name/volume_number/case.xml
    """
    jurisdiction = Jurisdiction.objects.get(name=jurname)
    zip_filename = zip_filename if zip_filename else jurname + ".zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as archive:
        cases = CaseMetadata.objects.filter(jurisdiction=jurisdiction)

        for case in cases:
            reporter = case.reporter.short_name
            volume = case.volume.volume_number
            filename = case.slug + '.xml'
            path = "{0}/{1}/{2}".format(reporter, volume, filename)
            archive.writestr(path, resources.get_matching_case_xml(case.case_id))

    print("completed: jurisdiction " + jurname + ", zip filename " + zip_filename)


