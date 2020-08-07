import csv
import gzip
import hashlib
import os
import re
import signal
import subprocess
import sys
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from getpass import getpass

import django
import json
from random import randint
from pathlib import Path
from celery import group
from tqdm import tqdm

# set up Django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print("WARNING: Can't configure Django -- tasks depending on Django will fail:\n%s" % e)

from django.core import management
from django.db import connections, transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.conf import settings
from fabric.api import local
from fabric.decorators import task

from capapi.models import CapUser
from capdb.models import VolumeXML, VolumeMetadata, SlowQuery, Jurisdiction, Citation, CaseMetadata, \
    Court, Reporter, PageStructure, CaseAnalysis

import capdb.tasks as tasks
from scripts import set_up_postgres, data_migrations, \
    validate_private_volumes as validate_private_volumes_script, export, update_snippets
from scripts.helpers import copy_file, volume_barcode_from_folder, up_to_date_volumes, storage_lookup


@contextmanager
def open_subprocess(command):
    """ Call command as a subprocess, and kill when with block exits. """
    print("Starting: %s" % command)
    proc = subprocess.Popen(command, shell=True, stdout=sys.stdout, stderr=sys.stderr)
    try:
        yield
    finally:
        print("Killing: %s" % command)
        os.kill(proc.pid, signal.SIGKILL)


@task(alias='run')
def run_django(port="127.0.0.1:8000"):
    if os.environ.get('DOCKERIZED'):
        port = "0.0.0.0:8000"
    # run celerybeat in background for elasticsearch indexing
    with open_subprocess("watchmedo auto-restart -d ./ -p '*.py' -R -- celery worker -A config.celery.app -c 1 -B"):
        # This was `management.call_command('runserver', port)`, but then the Django autoreloader
        # itself calls fab run and we get two copies of everything!
        local("python manage.py runserver %s" % port)


@task
def run_frontend(port=None):
    with open_subprocess("npm run serve"):
        run_django(port)


@task
def test():
    """ Run tests with coverage report. """
    local("pytest --fail-on-template-vars --cov --cov-report=")

@task(alias='pip-compile')
def pip_compile(args=''):
    import subprocess

    # run pip-compile
    # Use --allow-unsafe because pip --require-hashes needs all requirements to be pinned, including those like
    # setuptools that pip-compile leaves out by default.
    command = ['pip-compile', '--generate-hashes', '--allow-unsafe']+args.split()
    print("Calling %s" % " ".join(command))
    subprocess.check_call(command, env=dict(os.environ, CUSTOM_COMPILE_COMMAND='fab pip-compile'))
    update_docker_image_version()

@task
def update_docker_image_version():
    """
        Update the image version in docker-compose.yml to contain a hash of all files that affect the Dockerfile build.
    """
    import re

    # get hash of Dockerfile input files
    paths = ['Dockerfile', 'requirements.txt', 'yarn.lock']
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(Path(path).read_bytes())
    hash = hasher.hexdigest()[:32]

    # see if hash appears in docker-compose.yml
    docker_compose_path = Path(settings.BASE_DIR, 'docker-compose.yml')
    docker_compose = docker_compose_path.read_text()
    if hash not in docker_compose:

        # if hash not found, increment image version number, append new hash, and insert
        current_version = re.findall(r'image: capstone:(.*)', docker_compose)[0]
        digits = current_version.split('-')[0].split('.')
        digits[-1] = str(int(digits[-1])+1)
        new_version = "%s-%s" % (".".join(digits), hash)
        docker_compose = docker_compose.replace(current_version, new_version)
        docker_compose_path.write_text(docker_compose)
        print("%s updated to version %s" % (docker_compose_path, new_version))

    else:
        print("%s is already up to date" % docker_compose_path)

@task
def show_urls():
    """ Show routable URLs and their names, across all subdomains. """
    for name, host in settings.HOSTS.items():
        settings.URLCONF = host["urlconf"]
        print("\nURLs for %s (%s):\n" % (name, host["urlconf"]))
        management.call_command('show_urls', urlconf='URLCONF')


@task
def validate_private_volumes():
    """ Confirm that all volmets files in private S3 bin match S3 inventory. """
    validate_private_volumes_script.validate_private_volumes()


fixtures = [
    ('default', 'capweb', ('galleryentry', 'cmspicture', 'gallerysection')),
    ('capdb', 'capdb', ('jurisdiction', 'reporter', 'snippet', 'casefont')),
]

@task
def ingest_fixtures():
    for db, app, models in fixtures:
        management.call_command('loaddata', *models, database=db)


@task
def update_fixtures():
    for db, app, models in fixtures:
        for model in models:
            if model == 'volumemetadata':
                continue  # handle specially below
            output_path = Path(settings.BASE_DIR, '%s/fixtures/%s.%s.json.gz' % (app, model, db))
            print("Exporting %s to %s" % (model, output_path))
            with gzip.open(str(output_path), 'wt') as out:
                management.call_command('dumpdata', '%s.%s' % (app, model), database=db, stdout=out, indent=2)

@task
def export_volume(volume_id, output_zip=None):
    """
        Run this on production to export all data for a volume and its cases, as well as the volume's PDF, to a zip file.
        Use import_volume() to load the zip on dev.
    """
    from django.core import serializers
    import zipfile

    if output_zip is None:
        output_zip = '%s.zip' % volume_id
    print("Exporting volume to %s" % output_zip)

    to_serialize = set()
    volume = (VolumeMetadata.objects.filter(pk=volume_id)
        .select_related('request', 'created_by')
        .prefetch_related(
            Prefetch('page_structures', queryset=PageStructure.objects.select_related('ingest_source')),
            Prefetch('case_metadatas', queryset=(CaseMetadata.objects
                .select_related('structure', 'initial_metadata', 'body_cache', 'court', 'analysis')
                .prefetch_related('citations', 'extractedcitations'))),
        ).get()
    )
    to_serialize.add(volume)
    if volume.request:
        to_serialize.add(volume.request)
    if volume.created_by:
        to_serialize.add(volume.created_by)
    for page_structure in volume.page_structures.all():
        to_serialize.add(page_structure)
        to_serialize.add(page_structure.ingest_source)
    for case in volume.case_metadatas.all():
        to_serialize.add(case)
        to_serialize.add(case.structure)
        to_serialize.add(case.initial_metadata)
        to_serialize.add(case.body_cache)
        to_serialize.add(case.court)
        to_serialize.update(case.citations.all())
        to_serialize.update(case.extractedcitations.all())
        to_serialize.update(case.analysis.all())
    serializer = serializers.get_serializer("json")()
    with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zip:
        zip.writestr("volume.json", serializer.serialize(to_serialize))
        if volume.pdf_file:
            with volume.pdf_file.open() as pdf:
                zip.writestr("downloads/%s" % volume.pdf_file, pdf.read())

@task
def import_volume(volume_zip_path):
    """
        Run this on dev to import all data for a volume and its cases, as well as the volume's PDF.
        Use export_volume() on prod to generate zips for this function.
    """
    from distutils.dir_util import copy_tree
    import zipfile
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(volume_zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)
        management.call_command('loaddata', str(Path(tmpdirname, 'volume.json')), database='capdb')
        copy_tree(str(Path(tmpdirname, 'downloads')), str(Path(settings.BASE_DIR, 'test_data/downloads')))


@task
def run_pending_migrations():
    data_migrations.run_pending_migrations()

@task
def update_postgres_env(db='capdb'):
    set_up_postgres.update_postgres_env(db=db)


@task
def update_volume_metadata():
    """ Update VolumeMetadata fields from VolumeXML. """
    for volume_xml_id in VolumeXML.objects.values_list('pk', flat=True):
        tasks.update_volume_metadata.delay(volume_xml_id)

@task
def create_or_update_case_metadata(update_existing=False):
    """
        create or update CaseMetadata objects using celery
        - if update_existing, create and update
        - else, just create cases if missing
    """
    update_existing = True if update_existing else False
    tasks.create_case_metadata_from_all_vols(update_existing=update_existing)

@task
def init_dev_db():
    """
        Set up new dev database.
    """
    from django.contrib.auth.models import Group

    migrate()

    # fixtures
    if input("Create DEV admin user and fixtures on %s? (y/n) " % settings.DATABASES["default"]["HOST"]) == "y":
        CapUser.objects.create_superuser('admin@example.com', 'Password2')

        # create contract_approvers group and user
        approvers_group = Group(name='contract_approvers')
        approvers_group.save()
        approver = CapUser.objects.create_user('approver@example.com', 'Password2', first_name='Contract', last_name='Approver', email_verified=True)
        approver.groups.add(approvers_group)

@task
def migrate():
    """
        Migrate all dbs at once
    """

    management.call_command('migrate', database="default")
    management.call_command('migrate', database="capdb")
    management.call_command('migrate', database="user_data")

    update_postgres_env()

@task
def populate_search_index(last_run_before=None):
    tasks.run_task_for_volumes(
        tasks.update_elasticsearch_for_vol,
        VolumeMetadata.objects.exclude(out_of_scope=True),
        last_run_before=last_run_before)

@task
def rebuild_search_index(force=False):
    if force:
        management.call_command('search_index', '--delete', '-f')
        management.call_command('search_index', '--create', '-f')
    else:
        management.call_command('search_index', '--delete')
        management.call_command('search_index', '--create')
    populate_search_index()

@task
def update_search_index_settings():
    """ Update settings on existing index, based on the case_index.settings() call in capapi.documents. """
    from capapi.documents import case_index
    # remove settings that cannot be changed on existing indexes
    new_settings = {k:v for k, v in case_index._settings.items() if k not in ('number_of_shards')}
    case_index.put_settings(body={"index": new_settings})


@task
def add_permissions_groups():
    """
    Add permissions groups for admin panel
    """
    # add capapi groups
    management.call_command('loaddata', 'capapi/fixtures/groups.yaml')


@task
def export_cases(*changes):
    """
        Export all cases from Elasticsearch to download/bulk_exports/<timestamp>.
        Set up a new set of folders for a bulk data version, and queue jobs to export each jurisdiction and reporter.
        Example usage: fab 'export_cases:change 1\, with a comma,change 2'
    """
    export.init_export('* '+'\n* '.join(changes)+'\n')


@task
def retry_export_cases(version_string):
    """
        Requeue all the jobs to export files to download/bulk_exports/<version_string>.
        Jobs that see existing exported files will immediately exit, so this can be run to pick
        up an existing export_cases() bulk export where it left off.
    """
    export.export_all(version_string)


@task
def make_latest_folder(target_path, latest_path=None):
    """
        Create a "latest" version of a datestamped folder in the downloads area, symlinking to the original files.
        Example: fab make_latest_folder:bulk_exports/20200101
    """
    from capdb.storages import download_files_storage
    if not latest_path:
        latest_path = str(Path(target_path).with_name('latest'))

    # remove existing latest_path
    if download_files_storage.exists(latest_path):
        if input("%s already exists. Delete and replace? [y/N] " % latest_path) != 'y':
            return
        download_files_storage.rmtree(latest_path)

    # create new latest_path
    for path in download_files_storage.iter_files_recursive(target_path):
        new_path = str(Path(latest_path) / Path(path).relative_to(target_path))
        new_path = re.sub(r'_\d{8}\b', '', new_path)  # remove dates
        new_path_dir = str(Path(new_path).parent)
        download_files_storage.mkdir(new_path_dir, parents=True, exist_ok=True)
        symlink_val = os.path.relpath(path, new_path_dir)
        print(new_path, symlink_val)
        download_files_storage.symlink(symlink_val, new_path)


@task
def write_inventory_files(output_directory=os.path.join(settings.BASE_DIR, 'test_data/inventory/data')):
    """ Create inventory.csv.gz files in test_data/inventory/data. Should be re-run if test_data/from_vendor changes. """

    # get list of all files in test_data/from_vendor
    results = []
    for dir_name, subdir_list, file_list in os.walk(os.path.join(settings.BASE_DIR, 'test_data/from_vendor')):
        for file_path in file_list:
            if file_path == '.DS_Store':
                continue
            file_path = os.path.join(dir_name, file_path)

            # for each file, get list of [bucket, path, size, mod_time, md5, multipart_upload]
            results.append([
                'harvard-ftl-shared',
                file_path[len(os.path.join(settings.BASE_DIR, 'test_data/')):],
                os.path.getsize(file_path),
                datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                hashlib.md5(open(file_path, 'rb').read()).hexdigest(),
                'FALSE',
            ])

    # write results, split in half, to two inventory files named test_data/inventory/data/1.csv.gz and test_data/inventory/data/2.csv.gz
    for out_name, result_set in (("1", results[:len(results)//2]), ("2", results[len(results)//2:])):
        with gzip.open(os.path.join(output_directory, '%s.csv.gz' % out_name), "wt") as f:
            csv_w = csv.writer(f)
            for row in result_set:
                csv_w.writerow(row)

@task
def test_slow(jobs="1", ram="10", cpu="30"):
    """ For testing celery autoscaling, launch N jobs that will waste RAM and CPU. """
    from capdb.tasks import test_slow
    import time

    print("Running %s test_slow jobs and waiting for results ..." % jobs)
    jobs = int(jobs)
    job = group(test_slow.s(i=i, ram=int(ram), cpu=int(cpu)) for i in range(jobs))
    start_time = time.time()
    result = job.apply_async()
    result.get()  # wait for all jobs to finish
    run_time = time.time() - start_time
    print("Ran %s test_slow jobs in %s seconds (%s seconds/job)" % (jobs, run_time, run_time/jobs))

@task
def fix_md5_columns():
    """ Run celery tasks to fix orig_xml and md5 column for all volumes. """
    for volume_id in VolumeXML.objects.values_list('pk', flat=True):
        tasks.fix_md5_column.delay(volume_id)

@task
def show_slow_queries(server='capstone'):
    """
    Show slow queries for consumption by Slack bot.
    This requires

        shared_preload_libraries = 'pg_stat_statements'

    in postgresql.conf, that

        CREATE EXTENSION pg_stat_statements;

    has been run for the capstone database, and that

        GRANT EXECUTE ON FUNCTION pg_stat_statements_reset() TO <user>;

    has been run for the capstone user.
    """
    cursor = django.db.connections['capdb'].cursor()
    with open('../services/postgres/s1_pg_stat_statements_top_total.sql') as f:
        sql = f.read()
        cursor.execute(sql)
    try:
        rows = cursor.fetchall()
        today = datetime.now().strftime("%Y-%m-%d")
        heading = "*slow query report for %s on %s*" % (server, today)
        queries = []
    except Exception:
        print(json.dumps({'text': 'Could not get slow queries'}))
        return
    for row in rows:
        call_count, run_time, query = row[0], row[1], row[8]

        # fetch query from DB log and update last seen time
        saved_query, created = SlowQuery.objects.get_or_create(query=query)
        if not created:
            saved_query.save(update_fields=['last_seen'])

        if run_time/float(call_count) > 100.0:
            queries.append({
                'fallback': saved_query.label or query,
                'title': "%d call%s, %.1f ms, %.1f ms/query" % (
                    call_count, "" if call_count == 1 else "s", run_time, run_time/float(call_count)
                ),
                'text': saved_query.label or "```%s```" % query
            })

    if queries:
        print(json.dumps({'text': heading, 'attachments': queries}))
    cursor.execute("select pg_stat_statements_reset();")


@task
def create_fixtures_db_for_benchmarking():
    """
    In settings_dev mark TEST_SLOW_QUERIES as True
    """
    try:
        local('psql -c "CREATE DATABASE %s;"' % settings.TEST_SLOW_QUERIES_DB_NAME)
        init_dev_db()
    except Exception:
        # Exception is thrown if test db has already been created
        pass

    migrate()


@task
def create_case_fixtures_for_benchmarking(amount=50000, randomize_casemets=False):
    """
    Create an amount of case fixtures.
    This tasks assumes the existence of some casemet xmls in test_data

    Make sure that you have the necessary jurisdictions for this task.
    """
    from test_data.test_fixtures.factories import CaseXMLFactory
    if randomize_casemets:
        # get all casemet paths to choose a random casemet xml
        # for test case creation
        casemet_paths = []
        d = os.path.join(settings.BASE_DIR, "test_data/from_vendor/")
        for root, dirs, files in os.walk(d):
            for name in files:
                if "_redacted_CASEMETS" in name:
                    casemet_paths.append(os.path.join(root, name))
        amount_of_paths = len(casemet_paths) - 1
    else:
        case_xml = (Path(settings.BASE_DIR) / "test_data/from_vendor/32044057892259_redacted/casemets/32044057892259_redacted_CASEMETS_0001.xml").read_text()

    for _ in range(amount):
        if randomize_casemets:
            case_xml = (Path(casemet_paths[randint(0, amount_of_paths)])).read_text()
        try:
            # create casexml and casemetadata objects, save to db
            CaseXMLFactory(orig_xml=case_xml)
        except Exception:
            # Exception could happen because of duplicate slug keys on jurisdiction creation
            # For now, skipping this issue
            pass


@task
def tear_down_case_fixtures_for_benchmarking():
    """
    Make sure to mark settings_dev.TEST_SLOW_QUERIES as False
    """
    local('psql -c "DROP DATABASE %s;"' % settings.TEST_SLOW_QUERIES_DB_NAME)


@task
def count_data_per_jurisdiction(jurisdiction_id=None, write_to_file=True):
    """
    Run some basic analytics for visualization purposes
    """
    jurs = [jurisdiction_id] if jurisdiction_id else list(Jurisdiction.objects.all().order_by('id').values_list('id', flat=True))
    results = {}

    if write_to_file:
        # make sure we have a directory to write to
        file_dir = settings.DATA_COUNT_DIR
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)

    for jur in jurs:
        jur_results = {
            'case_count': tasks.get_case_count_for_jur(jur),
            'reporter_count': tasks.get_reporter_count_for_jur(jur),
            'court_count': tasks.get_court_count_for_jur(jur),
        }
        if write_to_file:
            file_path = os.path.join(file_dir, "%s.json" % jur)
            with open(file_path, 'w+') as f:
                json.dump(jur_results, f)

        results[jur] = jur_results

    if write_to_file:
        file_path = os.path.join(file_dir, "totals.json")
        with open(file_path, 'w+') as f:
            json.dump(results, f)
    else:
        return results

@task
def count_case_totals(write_to_file=True, min_year=1640):
    """
    Gets case counts for every jurisdiction through every recorded year
    compiles into json or returns results
    """

    jurs = list(Jurisdiction.objects.all().order_by('id').values_list('id', flat=True))
    file_dir = settings.DATA_COUNT_DIR
    warning = """Data per jurisdiction hasn\'t been compiled yet.
               \nMake sure to run `fab count_data_per_jurisdiction` first."""
    results = {}

    if not os.path.exists(file_dir):
        print(warning)
        return

    def assign_key(key):
        results[key] = {}

    # populate results with years
    [assign_key(year) for year in range(min_year, datetime.now().year+1)]

    for jur in jurs:
        file_path = os.path.join(file_dir, "%s.json" % jur)
        if not os.path.exists(file_path):
            print(warning)
            return

        with open(file_path, 'r') as f:
            jur_case_count = json.load(f)['case_count']['years']

        for year in results:
            str_year = str(year)
            results[year][jur] = jur_case_count[str_year] if str_year in jur_case_count else 0

    if write_to_file:
        file_path = os.path.join(file_dir, "totals.json")
        with open(file_path, 'w+') as f:
            json.dump(results, f)
    else:
        return results


@task
@transaction.atomic(using='capdb')
def fix_reporter_jurisdictions():
    """
        Update Reporter.jurisdictions values based on case jurisdictions.
        For regional reporters, reporter is associated with all jurisdictions for which it has cases.
        For other reporters, reporter is only associated with most frequent jurisdiction.
    """
    from capweb.helpers import select_raw_sql

    # clear existing relationships
    join_model = Reporter.jurisdictions.through
    join_model.objects.all().delete()

    # get count of cases in each jurisdiction for each reporter
    reporters = defaultdict(list)
    query = """SELECT reporter_id, jurisdiction_id, count(*) as case_count FROM capdb_casemetadata WHERE in_scope = true GROUP BY reporter_id, jurisdiction_id"""
    for row in select_raw_sql(query, using='capdb'):
        reporters[row.reporter_id].append([row.case_count, row.jurisdiction_id])

    # add reporter <-> jurisdiction relationship for primary jurisdiction for each reporter
    regional = Jurisdiction.objects.get(name='Regional')
    to_insert = []
    for reporter_id, jurisdictions in reporters.items():
        reporter = Reporter.objects.get(pk=reporter_id)
        jurisdictions.sort(reverse=True)

        # handle regional reporters
        if re.match(r'(A\.|P\.|S\.W\.|So\.|N\.W\.|N\.E\.)(\dd)?$', reporter.short_name):
            to_insert.append(join_model(reporter_id=reporter_id, jurisdiction_id=regional.id))
            for case_count, jurisdiction_id in jurisdictions:
                to_insert.append(join_model(reporter_id=reporter_id, jurisdiction_id=jurisdiction_id))

        # non-regional reporters
        else:
            to_insert.append(join_model(reporter_id=reporter_id, jurisdiction_id=jurisdictions[0][1]))

    join_model.objects.bulk_create(to_insert)


@task
def compress_volumes(*barcodes, storage_name='ingest_storage', max_volumes=10):
    """
        To compress a single volume:

            fab compress_volumes:32044057891608_redacted
            fab compress_volumes:32044057891608_unredacted,storage_name=private_ingest_storage

        To compress first N redacted volumes:

            fab compress_volumes:max_volumes=5

        To compress all volumes (including unredacted):

            fab compress_volumes:max_volumes=0

        ---

        To test local compression of volumes:

        First build docker container:
            docker build -t compress-worker -f ../services/docker/compress-worker.dockerfile .

        Next run fab task:
            docker run -v `pwd`:/app/ compress-worker fab compress_volumes
    """
    import capdb.storages
    import scripts.compress_volumes

    max_volumes = int(max_volumes)

    def get_volumes():
        """ Get all up-to-date volumes. """
        for storage_name in ('ingest_storage', 'private_ingest_storage'):
            storage = getattr(capdb.storages, storage_name)
            volumes = storage.iter_files("")
            current_vol = next(volumes, "")
            while current_vol:
                next_vol = next(volumes, "")
                if volume_barcode_from_folder(current_vol) != volume_barcode_from_folder(next_vol):
                    yield storage_name, current_vol
                current_vol = next_vol

    if barcodes:
        # get folder for each barcode provided at command line
        storage = getattr(capdb.storages, storage_name)
        barcodes = [(storage_name, max(storage.iter_files(barcode, partial_path=True))) for barcode in barcodes]
    else:
        # get latest folder all volumes
        barcodes = get_volumes()

    for i, args in enumerate(barcodes):
        scripts.compress_volumes.compress_volume.delay(*args)
        if max_volumes and i >= max_volumes:
            break


@task
def validate_captar_volumes():
    from capdb.storages import captar_storage
    import scripts.compress_volumes
    for folder in ('redacted', 'unredacted'):
        for volume_name in captar_storage.iter_files(folder):
            scripts.compress_volumes.validate_volume.delay(volume_name)

@task
def list_missing_captar_volumes():
    """ List all up-to-date folders in ingest storage that aren't in captar_storage yet. """
    from capdb.storages import captar_storage
    for storage_name in ['ingest_storage', 'private_ingest_storage']:
        print("Checking %s..." % storage_name)
        storage, path_prefix = storage_lookup[storage_name]
        print("- listing source folders")
        expected_files = set(str(path)+'.tar' for _, path in tqdm(up_to_date_volumes(storage.iter_files(""))))
        print("\n- listing captar archives")
        dest_files = set(path.rsplit('/', 1)[-1] for path in tqdm(captar_storage.iter_files_recursive(path_prefix)) if path.endswith('.tar'))
        print()
        missing = expected_files - dest_files
        if missing:
            print("- missing from captar_storage/%s:\n%s" % (path_prefix, "\n".join(missing)))
        else:
            print("- all volumes finished")


@task
def ngram_jurisdictions(slug=None):
    """ Generate ngrams for all jurisdictions, or for single jurisdiction if jurisdiction slug is provided. """
    from scripts.ngrams import ngram_jurisdictions
    ngram_jurisdictions(slug)


@task
def url_to_js_string(target_url="http://case.test:8000/maintenance/?no_toolbar", out_path="maintenance.html", new_domain="case.law"):
    """ Save target URL and all assets as a single Javascript-endoded HTML string. """
    import webpage2html
    from urllib.parse import urljoin, urlparse
    from mincss.processor import Processor
    import re
    from django.utils.html import escapejs

    # prefill webpage2html with reduced css files from mincss, removing unused styles
    p = Processor()
    p.process_url(target_url)
    p.process()
    for asset in p.links:
        href = urljoin(target_url, asset.href)
        content = asset.after
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.S)  # remove css comments
        webpage2html.webpage2html_cache[href] = content

    # use webpage2html to capture target_url as single string
    data = webpage2html.generate(target_url)
    data = data.replace("\n", "")   # remove linebreaks
    if new_domain:
        # replace case.test:8000 with case.law
        data = data.replace(urlparse(target_url).netloc, new_domain)
    data = escapejs(data)           # encode for storage in javascript
    Path(out_path).write_text(data)


@task
def run_edit_script(script=None, dry_run='true', **kwargs):
    """
        Run any of the scripts in scripts/edits. Usage: fab run_edit_script:script_name,dry_run=false. dry_run defaults to true.
    """
    from django.utils.module_loading import import_string

    # print list of scripts if no script name is provided
    if not script:
        options = Path(settings.BASE_DIR, 'scripts/edits').glob('*.py')
        print("Usage: run_edit_script:script, where script is one of:\n- %s" % ("\n- ".join(o.stem for o in options)))
        return

    # call provided script
    dry_run = dry_run != 'false'
    import_path = 'scripts.edits.%s.make_edits' % script
    try:
        method = import_string(import_path)
    except ImportError:
        print("Script not found. Attempted to import %s" % import_path)
    else:
        method(dry_run=dry_run, **kwargs)

@task
def update_all_snippets():
    update_snippets.update_all()

@task
def update_search_snippets():
    update_snippets.search_reporter_list()
    update_snippets.search_court_list()
    update_snippets.search_jurisdiction_list()

@task
def ice_volumes(scope='all', dry_run='true'):
    """
    For each captar'd volume that validated OK, tag the matching objects
    in the shared or private bucket for transfer to glacier and delete matching
    objects from the transfer bucket.

    Set dry_run to 'false' to run in earnest.
    """
    from capdb.storages import captar_storage
    from scripts.ice_volumes import recursively_tag
    from scripts.helpers import storage_lookup

    print("Preparing validation hash...")
    # validation paths look like 'validation/redacted/barcode[_datetime].txt'
    validation = {}
    for validation_path in tqdm(captar_storage.iter_files_recursive(path='validation/')):
        if validation_path.endswith('.txt'):
            validation_folder = validation_path.split('/')[2][:-4]
            if scope == 'all' or scope in validation_folder:
                validation[validation_folder] = False
                result = json.loads(captar_storage.contents(validation_path))
                if result[0] == "ok":
                    validation[validation_folder] = True
    print("Done.")

    # iterate through volumes in both storages, in reverse order,
    # alphabetically, tracking current barcode and tagging matching
    # volumes once a valid CAPTAR has been seen
    for storage_name in ['ingest_storage', 'private_ingest_storage']:
        print("Checking %s..." % storage_name)
        storage = storage_lookup[storage_name][0]
        last_barcode = None
        valid = False
        # volume paths look like 'barcode_[un]redacted/' or 'barcode_[un]redacted_datetime/'
        for volume_path in tqdm(reversed(list(storage.iter_files()))):
            barcode = volume_barcode_from_folder(volume_path)
            if barcode != last_barcode:
                last_barcode = barcode
                valid = False
            elif valid:
                # tag this volume and go on to the next
                if scope == 'all' or scope in volume_path:
                    recursively_tag.delay(storage_name, volume_path, dry_run=dry_run)
                continue
            else:
                pass
            try:
                if validation[volume_path.rstrip('/')]:
                    # tag this and all until barcode changes
                    if scope == 'all' or scope in volume_path:
                        recursively_tag.delay(storage_name, volume_path, dry_run=dry_run)
                    valid = True
            except KeyError:
                # we don't have a validation
                pass


@task
def sample_captar_images(output_folder='samples'):
    """
        Extract 100th image from each captar volume and store in captar_storage/samples.
    """
    from capdb.storages import CaptarStorage, captar_storage
    from io import BytesIO
    import random

    print("Getting list of existing sampled volumes to skip.")
    existing_barcodes = set(i.split('/', 1)[1].rsplit('_', 2)[0] for i in captar_storage.iter_files_recursive(output_folder))

    for folder in ('redacted', 'unredacted'):
        volume_folders = list(captar_storage.iter_files(folder))
        random.shuffle(volume_folders)
        for volume_folder in volume_folders:
            if volume_barcode_from_folder(volume_folder) in existing_barcodes:
                print("Skipping %s, already exists" % volume_folder)
                continue
            print("Checking %s" % volume_folder)
            volume_storage = CaptarStorage(captar_storage, volume_folder)
            images = sorted(i for i in volume_storage.iter_files('images') if i.endswith('.jpg'))
            if images:
                image = images[:100][-1]
                out_path = str(Path(output_folder, folder, Path(image).name))
                print("- Saving %s" % out_path)
                captar_storage.save(
                    out_path,
                    BytesIO(volume_storage.contents(image, 'rb'))  # passing file handle directly doesn't work because S3 storage strips file wrappers
                )

@task
def make_pdfs(volume_path=None, replace_existing=False):
    """
        Call scripts.make_pdf for all redacted and unredacted volumes, or for single path like 'redacted/<barcode>'
    """
    from scripts.make_pdf import make_pdf
    from capdb.storages import captar_storage
    from itertools import chain

    if volume_path:
        make_pdf.delay(volume_path, replace_existing=replace_existing)
    else:
        print("Adding volumes to celery queue:")
        for barcode, volume_path in tqdm(chain(up_to_date_volumes(captar_storage.iter_files('redacted')), up_to_date_volumes(captar_storage.iter_files('unredacted')))):
            make_pdf.delay(str(volume_path), replace_existing=replace_existing)

@task
def captar_to_token_stream(*volume_barcodes, replace_existing=False, key=settings.REDACTION_KEY, save_failed=False, catch_validation_errors=False):
    """
        Convert captar volumes to token stream zip files to be imported.
    """
    import scripts.refactor_xml
    from getpass import getpass
    import nacl.secret, nacl.encoding
    from capdb.storages import captar_storage

    # get key
    if not key:
        key = getpass("Enter REDACTION_KEY (e.g. DPpSaf/iGNmq/3SYOPH6LfCZ9jUFkuoGKXycb2Of5Ms=): ")

    # make sure key is valid
    nacl.secret.SecretBox(force_bytes(key), encoder=nacl.encoding.Base64Encoder)

    # find existing zips in token_streams to skip recreating
    if not replace_existing:
        existing_vols = {Path(p).stem for p in captar_storage.iter_files('token_streams')}

    # get list of all redacted vols and unredacted vols
    redacted_vols = up_to_date_volumes(captar_storage.iter_files('redacted'))
    if volume_barcodes:
        volume_barcodes = set(volume_barcodes)
        redacted_vols = [i for i in redacted_vols if i[0] in volume_barcodes]
    unredacted_vols = dict(up_to_date_volumes(captar_storage.iter_files('unredacted')))

    # zip each pair of volumes
    for barcode, redacted_path in redacted_vols:
        if barcode in unredacted_vols:
            primary_path = unredacted_vols[barcode]
            secondary_path = str(redacted_path)
        else:
            primary_path = redacted_path
            secondary_path = None
        if not replace_existing and primary_path.name in existing_vols:
            continue
        scripts.refactor_xml.volume_to_json.delay(barcode, str(primary_path), secondary_path, key=str(key), save_failed=save_failed, catch_validation_errors=catch_validation_errors)

@task
def validate_token_stream(volume_barcode, key=settings.REDACTION_KEY):
    """ Run just the reversability check from captar_to_token_stream; useful for debugging a previous failure. """
    import scripts.refactor_xml
    scripts.refactor_xml.test_reversability(volume_barcode, key)

@task
def load_token_streams(replace_existing=False):
    """
        Import token stream zip files created by captar_to_token_stream.
    """
    import scripts.refactor_xml
    from capdb.storages import captar_storage

    # find already-import volumes to skip re-importing
    if not replace_existing:
        already_imported = set(VolumeMetadata.objects.exclude(xml_metadata=None).values_list('barcode', flat=True))

    # import zips
    zip_paths = up_to_date_volumes(captar_storage.iter_files('token_streams'))
    for volume_barcode, path in zip_paths:
        if not replace_existing and volume_barcode in already_imported:
            continue
        scripts.refactor_xml.write_to_db.delay(volume_barcode, str(path))


@task
def refresh_case_body_cache(last_run_before=None, rerender=True):
    """ Recreate CaseBodyCache for all cases. Use `fab refresh_case_body_cache:rerender=false` to just regenerate text/json from html. """
    tasks.run_task_for_volumes(
        tasks.sync_case_body_cache_for_vol,
        VolumeMetadata.objects.exclude(xml_metadata=None),
        last_run_before=last_run_before,
        rerender=rerender != 'false',
    )


@task
def run_text_analysis(last_run_before=None):
    """ Call run_text_analysis for all cases. """
    tasks.run_task_for_volumes(
        tasks.run_text_analysis_for_vol,
        VolumeMetadata.objects.exclude(out_of_scope=True),
        last_run_before=last_run_before,
    )


@task
def sync_from_initial_metadata(last_run_before=None, force=False):
    """ Call sync_from_initial_metadata on all cases. Use force=1 to re-run on already synced cases (not recommended)."""
    tasks.run_task_for_volumes(
        tasks.sync_from_initial_metadata_for_vol,
        VolumeMetadata.objects.exclude(xml_metadata=None),
        last_run_before=last_run_before,
        force=force,
    )

@task
def update_case_frontend_url(update_existing=False):
    """
        Update CaseMetadata.frontend_url value for all cases.
    """
    import itertools
    from scripts.helpers import ordered_query_iterator
    # get a set of all ambiguous_cites that appear more than once -- these should be linked by ID
    cursor = django.db.connections['capdb'].cursor()
    cursor.execute("SELECT DISTINCT a.cite FROM capdb_citation a, capdb_citation b WHERE a.cite=b.cite AND a.id<b.id")
    ambiguous_cites = {row[0] for row in cursor.fetchall()}
    # loop through all cites in batches of 10000
    cites = Citation.objects.select_related('case').only('cite', 'case__reporter_id', 'case__volume_id').order_by('case_id', 'id')
    if not update_existing:
        cites = cites.filter(case__frontend_url=None)
    cites = ordered_query_iterator(cites, chunk_size=10000)
    cite_groups = itertools.groupby(cites, key=lambda cite: cite.case_id)
    # set frontend_url for each case
    case_batch = []
    for k, cite_group in tqdm(cite_groups):
        cite_group = list(cite_group)
        cite = next((c for c in cite_group if c.type == 'official'), cite_group[0])
        case = cite.case
        new_frontend_url = case.get_frontend_url(cite, include_host=False, disambiguate=cite.cite in ambiguous_cites)
        if new_frontend_url != case.frontend_url:
            case.frontend_url = new_frontend_url
            case_batch.append(case)
            if len(case_batch) > 1000:
                CaseMetadata.objects.bulk_update(case_batch, ['frontend_url'])
                case_batch = []
    if case_batch:
        CaseMetadata.objects.bulk_update(case_batch, ['frontend_url'])

@task
def run_script(module_path, function_name='main', *args, **kwargs):
    """ Run an arbitrary function, e.g. fab run_script:module.name,func_name,arg1,arg2 """
    from django.utils.module_loading import import_string
    func = import_string("%s.%s" % (module_path, function_name))
    func(*args, **kwargs)

@task
def delete_empty_courts(dry_run='true'):
    """
        Delete empty courts, and reslug any other courts that are affected by the newly-available slug.
        NOTE: this may not be a good idea to run if users depend on stable court slugs.
    """
    from django.db import transaction
    import re
    courts_to_delete = set(Court.objects.filter(case_metadatas=None))
    for court_to_delete in sorted(courts_to_delete, key=lambda c: c.slug):
        m = re.match(r'(.*?)(?:-(\d+))?$', court_to_delete.slug)
        prefix, num = m.groups()
        matches = list(Court.objects.filter(slug__startswith=prefix).order_by('slug'))
        reslug = []
        for cc in matches:
            m = re.match(r'%s-(\d+)$' % re.escape(prefix), cc.slug)
            if m and (not num or int(num) < int(m.group(1))) and cc not in courts_to_delete:
                reslug.append(cc)
        with transaction.atomic(using='capdb'):
            if dry_run == 'false':
                print("Deleting %s" % court_to_delete)
                court_to_delete.delete()
            else:
                print("Would delete %s" % court_to_delete)
            for court_to_reslug in reslug:
                if dry_run == 'false':
                    print(" - Reslugging %s" % court_to_reslug)
                    court_to_reslug.slug = None
                    court_to_reslug.save()
                else:
                    print(" - Would reslug %s" % court_to_reslug)


@task
def update_in_scope(last_run_before=None):
    tasks.run_task_for_volumes(tasks.update_in_scope_for_vol, last_run_before=last_run_before)


@task
def retrieve_and_store_images(last_run_before=None):
    """ Retrieve images from inside cases """
    tasks.run_task_for_volumes(tasks.retrieve_images_from_cases, last_run_before=last_run_before)

@task
def redact_id_numbers(last_run_before=None):
    tasks.run_task_for_volumes(tasks.remove_id_number_in_volume, last_run_before=last_run_before)

@task
def update_reporter_years(reporter_id=None):
    """
        Update Reporter.start_year and Reporter.end_year to match actual dates of cases.
        If reporter_id is supplied, only update that reporter.
    """
    cursor = django.db.connections['capdb'].cursor()
    cursor.execute("""
        update capdb_reporter r
        set start_year = new_start_year, end_year = new_end_year
        from capdb_reporter r2
        left join (
                 select c.reporter_id,
                        min(date_part('year', decision_date)) as new_start_year,
                        max(date_part('year', decision_date)) as new_end_year
                 from capdb_casemetadata c, capdb_volumemetadata v
                 where v.barcode=c.volume_id and c.in_scope is true and v.out_of_scope is false
                 %s
                 group by c.reporter_id
             ) as cases on cases.reporter_id = r2.id
        where r2.id=r.id %s;
    """ % (
        ("and c.reporter_id=%s" % reporter_id) if reporter_id else '',
        ("and r.id=%s" % reporter_id) if reporter_id else '',
    ))


@task
def check_existing_emails():
    """
        Report mailgun validity of all existing email accounts.
    """
    import requests
    import time
    emails = CapUser.objects.filter(is_active=True).values_list('email', flat=True)
    response = requests.post(
        "https://api.mailgun.net/v4/address/validate/bulk/emails",
        files={'file': ('report.csv', 'email\n%s\n' % "\n".join(emails))},
        auth=('api', settings.MAILGUN_API_KEY))
    print(response.json())
    while True:
        response = requests.get("https://api.mailgun.net/v4/address/validate/bulk/emails", auth=('api', settings.MAILGUN_API_KEY))
        print(response.json())
        if response.json()['status'] == 'uploaded':
            break
        time.sleep(1)
    response = requests.get(response.json()['download_url']['csv'])
    with open('email_report.csv.zip', 'wb') as out:
        out.write(response.content)


@task
def download_pdfs(jurisdiction=None):
    """
        Download all PDFs, or all for a jurisdiction, to download_files_storage.
    """
    from capdb.storages import pdf_storage, download_files_storage
    import re

    # find each PDF by checking TarFile, since we have a 1-to-1 mapping between tar files and PDFs
    volumes = (VolumeMetadata.objects.filter(out_of_scope=False, pdf_file='')
        .select_related('reporter', 'nominative_reporter')
        .prefetch_related('reporter__jurisdictions')
        .order_by('reporter__jurisdictions__slug', 'pk'))
    if jurisdiction:
        volumes = volumes.filter(reporter__jurisdictions__slug=jurisdiction)

    for volume in volumes:
        # get info about this volume
        source_path = "redacted/%s.pdf" % volume.pk
        print("Downloading %s ..." % source_path)
        reporter = volume.reporter
        jurisdiction = reporter.jurisdictions.first()

        # generate a path for the PDF, like:
        # PDFs / open / North Carolina / N.C. / 1 N.C. (1 Tay.).pdf
        new_name_prefix = '%s %s' % (volume.volume_number, reporter.short_name)
        if volume.nominative_reporter:
            new_name_prefix += ' (%s %s)' % (volume.nominative_volume_number, volume.nominative_reporter.short_name)
        new_name_prefix = re.sub(r'[\\/:*?"<>|]', '-', new_name_prefix)  # replace windows-illegal characters with -
        open_or_restricted = 'open' if jurisdiction.whitelisted else 'restricted'
        for i in range(10):
            # retry so we can append ' a', ' b', etc. for duplicate volumes
            new_name = new_name_prefix + (' %s' % chr(97+i) if i else '') + '.pdf'
            new_name = new_name.replace('..', '.')  # avoid double period in '1 Mass..pdf'
            new_path = Path('PDFs', open_or_restricted, jurisdiction.name_long, reporter.short_name, new_name)
            if not download_files_storage.exists(str(new_path)):
                break
        else:
            raise Exception("Failed to find a non-existent path for %s" % new_path)

        try:
            # copy file
            try:
                copy_file(source_path, new_path, from_storage=pdf_storage, to_storage=download_files_storage)
            except IOError:
                print("  - ERROR: source file not found")
                continue

            # save PDF location on volume model
            volume.pdf_file.name = str(new_path)
            volume.save()
            print("  - Downloaded to %s" % new_path)
        except Exception:
            # clean up partial downloads if process is killed
            download_files_storage.delete(str(new_path))
            raise


def unredact_volumes(volumes, dry_run='true'):
    key = getpass("Enter decryption key: ").strip() if dry_run == 'false' else None
    volumes = (volumes
        .filter(out_of_scope=False, redacted=True)
        .select_related('reporter')
        .order_by('publication_year', 'volume_number'))
    for volume in volumes:
        print("Unredacting %s %s (%s)" % (volume.volume_number, volume.reporter.short_name, volume.publication_year))
        if dry_run == 'false':
            volume.unredact(key)


@task
def unredact_out_of_copyright_volumes(dry_run='true'):
    from django.utils import timezone
    unredact_volumes(VolumeMetadata.objects.filter(publication_year__lt=timezone.now().year-95), dry_run)


@task
def unredact_jurisdiction_volumes(jurisdiction_slug, dry_run='true'):
    unredact_volumes(VolumeMetadata.objects.filter(reporter__jurisdictions__slug=jurisdiction_slug), dry_run)


@task
def populate_case_page_order():
    """
        Set all CaseMetadata.first_page_order and .last_page_order values based on PageStructure.
    """
    cursor = django.db.connections['capdb'].cursor()
    cursor.execute("""
        UPDATE capdb_casemetadata m
        SET first_page_order=j.first_page_order, last_page_order=j.last_page_order
        FROM
            capdb_casestructure c,
            (
                SELECT min(p.order) as first_page_order, max(p.order) as last_page_order, cp.casestructure_id
                FROM capdb_pagestructure p, capdb_casestructure_pages cp
                WHERE p.id=cp.pagestructure_id
                GROUP BY cp.casestructure_id
            ) j
        WHERE c.metadata_id=m.id and c.id=j.casestructure_id
    """)


@task
def extract_all_citations(last_run_before=None):
    """ extract citations """
    tasks.run_task_for_volumes(tasks.extract_citations_per_vol, last_run_before=last_run_before)


@task
def export_citation_graph(output_folder="graph"):
    """writes cited from and citing to to file"""
    from django.utils import timezone
    from django.contrib.postgres.aggregates import ArrayAgg

    # create path if doesn't exist
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    citations_path = output_folder / 'citations.csv.gz'
    citations_path.touch(mode=0o644)  # check that we have write access

    # write citations.csv.gz
    nodes = set()
    edge_count = 0
    chunk_size = 10000
    query = """
        DECLARE cite_cursor CURSOR for
        select
            from_id, array_agg(distinct to_id)
        from (
            select
                cite_from.id as from_id, min(cite_to.id) as to_id
            from capdb_casemetadata cite_from
            inner join
                capdb_extractedcitation ec on cite_from.id = ec.cited_by_id
            inner join
                capdb_citation cite on cite.normalized_cite = ec.normalized_cite
            inner join
                capdb_casemetadata cite_to on cite.case_id = cite_to.id
            where 
                cite_from.in_scope is true
                and cite_to.in_scope is true
                and cite_from.decision_date_original >= cite_to.decision_date_original
                and cite_to.id != cite_from.id
            group by cite_from.id, ec.normalized_cite
            having count(*) = 1
        ) as c group by from_id;
    """
    print("Running citations query")
    with transaction.atomic(using='capdb'), \
            connections['capdb'].cursor() as cursor, \
            gzip.open(str(citations_path), "wt") as f, \
            tqdm() as pbar:
        csv_w = csv.writer(f)
        cursor.execute(query)
        while True:
            cursor.execute("FETCH %s FROM cite_cursor" % chunk_size)
            chunk = cursor.fetchall()
            pbar.update()
            if not chunk:
                break
            for row in chunk:
                out = [row[0]] + row[1]
                csv_w.writerow(out)
                nodes.update(out)
                edge_count += len(out) - 1

    # write README.txt
    output_folder.joinpath('README.md').write_text(
        "Citation graph exported %s:\n\n"
        "* Nodes: %s\n"
        "* Edges: %s\n" % (timezone.now(), len(nodes), edge_count)
    )

    # write metadata.csv.gz
    metadata_fields = [
        'id', 'frontend_url', 'jurisdiction__name', 'jurisdiction_id', 'court__name_abbreviation', 'court_id',
        'reporter__short_name', 'reporter_id', 'name_abbreviation', 'decision_date_original', 'cites'
    ]
    nodes = list(nodes)
    print("Writing metadata")
    metadata = {}
    with gzip.open(str(output_folder / 'metadata.csv.gz'), "wt") as f:
        csv_w = csv.writer(f)
        csv_w.writerow(metadata_fields)
        query = CaseMetadata.objects.annotate(cites=ArrayAgg('citations__cite')).values_list(*metadata_fields)
        for i in tqdm(range(0, len(nodes), chunk_size)):
            for row in query.filter(id__in=nodes[i:i+chunk_size]):
                row = row[:-1] + ("; ".join(row[-1]),)  # combine citations
                metadata[row[0]] = row
                csv_w.writerow(row)

    ### write outputs per-jurisdiction --
    print("Writing jurisdiction files")

    # read back through the adjacency list and write each row to the appropriate subfolder
    jurisdictions = {}
    jurs_folder = output_folder / 'by_jurisdiction'
    jurs_folder.mkdir(parents=True, exist_ok=True)
    jurs_folder.joinpath('README.md').write_text("Subsets of the full graph consisting only of citations between cases within a particular jurisdiction.")
    with gzip.open(str(citations_path), 'rt') as f:
        reader = csv.reader(f)
        for ids in tqdm(reader):
            # filter to only in-jurisdiction cites
            ids = [int(i) for i in ids]
            jur_name = metadata[ids[0]][2]
            ids = [id for id in ids if metadata[id][2] == jur_name]
            if len(ids) < 2:
                continue

            # if this is the first time we're seeing this jurisdiction, set up output streams for the
            # adjacency list and metadata
            if jur_name not in jurisdictions:
                jur_folder = jurs_folder / jur_name
                jur_folder.mkdir(parents=True, exist_ok=True)
                graph_file = gzip.open(str(jur_folder / 'citations.csv.gz'), "wt")
                graph_file_writer = csv.writer(graph_file)
                metadata_file = gzip.open(str(jur_folder / 'metadata.csv.gz'), "wt")
                metadata_file_writer = csv.writer(metadata_file)
                metadata_file_writer.writerow(metadata_fields)
                nodes = set()
                jurisdictions[jur_name] = {
                    'name': jur_name,
                    'folder': jur_folder,
                    'nodes': nodes,
                    'graph_file': graph_file,
                    'graph_file_writer': graph_file_writer,
                    'metadata_file': metadata_file,
                    'metadata_file_writer': metadata_file_writer,
                    'edge_count': 0,
                }

            # write out adjacency list and metadata
            jur = jurisdictions[jur_name]
            nodes = jur['nodes']
            metadata_file_writer = jur['metadata_file_writer']
            jur['graph_file_writer'].writerow(ids)
            jur['edge_count'] += len(ids) - 1
            for id in ids:
                if id not in nodes:
                    nodes.add(id)
                    metadata_file_writer.writerow(metadata[id])

    # close streams for each jurisdiction and write out metadata
    for jur in jurisdictions.values():
        jur['graph_file'].close()
        jur['metadata_file'].close()
        jur['folder'].joinpath('README.md').write_text(
            "Citation graph for %s exported %s:\n\n"
            "* Nodes: %s\n"
            "* Edges: %s\n" % (jur['name'], timezone.now(), len(jur['nodes']), jur['edge_count'])
        )

    count_cites_by_year(output_folder, output_folder.joinpath('aggregations'))


@task
def report_missed_citations():
    """ Summarize files written by extract_all_citations. Writes csv to stdout. """
    import random
    counts = {}
    for f in Path(settings.MISSED_CITATIONS_DIR).glob('*.csv'):
        for line in csv.reader(f.read_text().splitlines()):
            reporters = json.loads(line[2])
            for reporter, count in reporters.items():
                if reporter not in counts:
                    counts[reporter] = {'count': 0, 'cases': []}
                counts[reporter]['count'] += count
                counts[reporter]['cases'].append(line[0])

    counts = dict((k, v) for k, v in counts.items() if v['count'] >= 10)
    for v in counts.values():
        random.shuffle(v['cases'])
    counts = sorted(([v['count'], k] + v['cases'][:5] for k, v in counts.items()), reverse=True)
    writer = csv.writer(sys.stdout)
    writer.writerows(counts)


@task
def count_cites_by_year(folder, output_folder):
    """ Write summaries from citation graph in folder to output_folder. """
    folder = Path(folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    print("Loading metadata")
    metadata = {}
    with gzip.open(str(folder / 'metadata.csv.gz'), "rt") as f:
        for row in tqdm(csv.DictReader(f)):
            metadata[int(row['id'])] = (int(row['jurisdiction_id']), int(row['decision_date_original'][:4]))
    cites_per_jurisdiction = defaultdict(int)
    totals = defaultdict(lambda: defaultdict(int))
    totals_by_year = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    print("Counting totals")
    with gzip.open(str(folder / 'citations.csv.gz'), "rt") as f:
        for row in tqdm(csv.reader(f)):
            from_id, *to_ids = [int(i) for i in row]
            from_jur_id, year = metadata[from_id]
            cites_per_jurisdiction[from_jur_id] += len(to_ids)
            for to_id in to_ids:
                to_jur_id = metadata[to_id][0]
                totals[from_jur_id][to_jur_id] += 1
                totals_by_year[year][from_jur_id][to_jur_id] += 1

    print("Writing output")
    jurisdiction_metadata = [
        {'id': j.id, 'slug': j.slug, 'name': j.name, 'name_long': j.name_long, 'cites': cites_per_jurisdiction[j.id]}
        for j in Jurisdiction.objects.filter(id__in=cites_per_jurisdiction.keys()).order_by('name')
    ]
    output_folder.joinpath('jurisdictions.json').write_text(json.dumps(jurisdiction_metadata))
    output_folder.joinpath('totals.json').write_text(json.dumps(totals))
    output_folder.joinpath('totals_by_year.json').write_text(json.dumps(totals_by_year))
    output_folder.joinpath('README.md').write_text(
        "This directory contains aggregations of data by jurisdiction from the citation graph:\n\n"
        "* jurisdictions.json: citation counts by citing jurisdiction\n"
        "* totals.json: citation counts from each jurisdiction to each jurisdiction\n"
        "* totals_by_year.json: citation counts from each jurisdiction to each jurisdiction for each year\n"
    )


@task
def filter_limerick_lines(stopwords_path):
    """
        Filter limerick_lines.js against a list of stopwords,
        such as https://www.freewebheaders.com/download/files/full-list-of-bad-words_text-file_2018_07_30.zip
        or https://www.cs.cmu.edu/~biglou/resources/bad-words.txt
    """
    import re
    stopwords_set = set(s.lower() for s in Path(stopwords_path).read_text().splitlines(keepends=False))
    limerick_text = Path('static/js/limerick_lines.js').read_text()
    assignment, limerick_json = limerick_text.split(' = ', 1)
    limericks = json.loads(limerick_json)
    all_blocked = set()
    for a in limericks.values():
        for b in a.values():
            for c in b.values():
                for word, sentences in c.items():
                    fixed = []
                    blocked_any = False
                    for sentence in sentences:
                        words = set(w.lower() for w in re.findall(r'\w+', sentence))
                        blocked = words & stopwords_set
                        all_blocked |= blocked
                        if blocked:
                            blocked_any = True
                            print("Removed ", sentence, blocked)
                        else:
                            fixed.append(sentence)
                    if blocked_any:
                        c[word] = fixed
    Path('static/js/limerick_lines_fixed.js').write_text(assignment + " = " + json.dumps(limericks))


@task
def write_manifest_files():
    """ Update manifest.csv in /download/ """
    from capdb.storages import download_files_storage
    with download_files_storage.open('manifest.csv', 'w') as out:
        writer = csv.writer(out)
        writer.writerow(["path", "size", "last_modified"])
        for path in tqdm(sorted(download_files_storage.iter_files_recursive())):
            stat = download_files_storage.stat(path)
            writer.writerow([
                path,
                stat.st_size,
                datetime.utcfromtimestamp(stat.st_mtime).replace(tzinfo=timezone.utc),
            ])


@task
def calculate_pagerank_scores(citation_graph_path="graph/citations.csv.gz", pagerank_score_output="graph/pagerank_scores.csv.gz"):
    """ Generate pageranks scores for all nodes in the given citation graph """
    import networkx as nx
    print("Reading citation graph")
    graph = nx.read_adjlist(citation_graph_path, delimiter=",", create_using=nx.DiGraph())
    print("Calculating PageRank")
    pagerank_scores = sorted(nx.pagerank(graph).items(), key=lambda x: x[1])
    print("Writing output")
    with gzip.open(pagerank_score_output, "wt") as f:
        csv_output = csv.writer(f)
        csv_output.writerow(['id','raw_score','percentile'])
        last_score = 0
        percentile = 0
        total_rows = len(pagerank_scores)
        for i, [id, score] in tqdm(enumerate(pagerank_scores)):
            if score > last_score:
                percentile = i
            csv_output.writerow([id, score, percentile/total_rows])


@task
def load_pagerank_scores(pagerank_score_output):
    with transaction.atomic(using='capdb'):
        CaseAnalysis.objects.filter(key__in='pagerank').delete()
        with gzip.open(pagerank_score_output, 'rt') as f:
            reader = csv.DictReader(f)
            objs = (CaseAnalysis(key='pagerank', value={'raw': float(line['raw_score']), 'percentile': float(line['percentile'])}, case_id=line['id']) for line in reader)
            CaseAnalysis.objects.bulk_create(objs)


if __name__ == "__main__":
    # allow tasks to be run as "python fabfile.py task"
    # this is convenient for profiling, e.g. "kernprof -l fabfile.py refresh_case_body_cache"
    from fabric.main import main
    main()

