import csv
import gzip
import hashlib
import os
import pathlib
import signal
import subprocess
import sys
from datetime import datetime
import django
import json
from random import randint
from pathlib import Path
from celery import shared_task, group
from tqdm import tqdm

# set up Django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print("WARNING: Can't configure Django -- tasks depending on Django will fail:\n%s" % e)

from django.core import management
from django.db import connections
from django.utils.encoding import force_str, force_bytes
from django.conf import settings
from fabric.api import local
from fabric.decorators import task

from capapi.models import CapUser
from capdb.models import VolumeXML, VolumeMetadata, CaseXML, SlowQuery, Jurisdiction, Citation, CaseMetadata, \
    Court

import capdb.tasks as tasks
from scripts import set_up_postgres, data_migrations, ingest_by_manifest, \
    validate_private_volumes as validate_private_volumes_script, export, update_snippets
from scripts.helpers import parse_xml, serialize_xml, copy_file, volume_barcode_from_folder, \
    up_to_date_volumes, storage_lookup


@task(alias='run')
def run_django(port="127.0.0.1:8000"):
    if os.environ.get('DOCKERIZED'):
        port = "0.0.0.0:8000"
    management.call_command('runserver', port)


@task
def run_frontend(port=None):
    node_proc = subprocess.Popen("npm run serve", shell=True, stdout=sys.stdout, stderr=sys.stderr)
    try:
        run_django(port)
    finally:
        os.kill(node_proc.pid, signal.SIGKILL)


@task
def test():
    """ Run tests with coverage report. """
    local("pytest --fail-on-template-vars --cov --cov-report=")

@task(alias='pip-compile')
def pip_compile(args=''):
    """
        We want to run `pip-compile --generate-hashes` so hash values of packages are locked.
        This breaks packages installed from source; pip currently refuses to install source packages alongside hashed packages:
            https://github.com/pypa/pip/issues/4995
        pip will install packages from github in gz form, but those are currently rejected by pip-compile:
            https://github.com/jazzband/pip-tools/issues/700
        So we need to keep package requirements in requirements.in that look like this:
            -e git+git://github.com/jcushman/email-normalize.git@6b5088bd05de247a9a33ad4e5c7911b676d6daf2#egg=email-normalize
        and convert them to https form with hashes once they're written to requirements.txt:
            https://github.com/jcushman/email-normalize/archive/6b5088bd05de247a9a33ad4e5c7911b676d6daf2.tar.gz#egg=email-normalize --hash=sha256:530851e150781c5208f0b60a278a902a3e5c6b98cd31d21f86eba54335134766
    """
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
def sync_with_s3():
    """ Import XML for volumes that have not had a previous completed import with that VolumeXML md5. """
    for volume_barcode in VolumeMetadata.objects.filter(ingest_status__in=['to_ingest', 'error']).values_list('barcode', flat=True):
        ingest_by_manifest.ingest_volume_from_s3.delay(volume_barcode)

@task
def total_sync_with_s3():
    """
        Inspect and import any changed XML for all volumes not yet imported.

        This now does the same thing as sync_with_s3, but is more efficient than sync_with_s3 for large numbers of volumes
        because it uses the S3 manifest.
    """
    ingest_by_manifest.sync_s3_data.delay(full_sync=False)

@task
def validate_private_volumes():
    """ Confirm that all volmets files in private S3 bin match S3 inventory. """
    validate_private_volumes_script.validate_private_volumes()


fixtures = [
    ('default', 'capweb', ('galleryentry', 'cmspicture', 'gallerysection')),
    ('capdb', 'capdb', ('jurisdiction', 'reporter', 'volumemetadata')),
]

@task
def ingest_fixtures():
    for db, app, models in fixtures:
        management.call_command('loaddata', *models, database=db)


@task
def update_fixtures():
    from django.core import serializers

    # write full tables
    for db, app, models in fixtures:
        for model in models:
            if model == 'volumemetadata':
                continue  # handle specially below
            output_path = Path(settings.BASE_DIR, '%s/fixtures/%s.%s.json.gz' % (app, model, db))
            print("Exporting %s to %s" % (model, output_path))
            with gzip.open(str(output_path), 'wt') as out:
                management.call_command('dumpdata', '%s.%s' % (app, model), database=db, stdout=out, indent=2)

    # write selected volumes with associated relationships
    barcodes = ('32044057891608', '32044061407086', '32044057892259', 'WnApp_199')
    to_serialize = set()
    for volume in VolumeMetadata.objects.filter(pk__in=barcodes).select_related('request', 'created_by'):
        to_serialize.add(volume)
        if volume.request:
            to_serialize.add(volume.request)
        if volume.created_by:
            to_serialize.add(volume.created_by)
    serializer = serializers.get_serializer("json")()
    with gzip.open(str(Path(settings.BASE_DIR, "capdb/fixtures/volumemetadata.capdb.json.gz")), "wt") as out:
        serializer.serialize(to_serialize, stream=out, indent=2)

@task
def run_pending_migrations():
    data_migrations.run_pending_migrations()

@task
def update_postgres_env(db='capdb'):
    set_up_postgres.update_postgres_env(db=db)

@task
def initialize_denormalization_fields():
    """
        Manually populate or repopulate denormalized fields.

        Typically initialize_denormalization_fields should instead be called in a migration that adds denormalized fields, as
            migrations.RunPython(initialize_denormalization_fields),
        but this allows it to be re-run manually if necessary.
    """
    set_up_postgres.initialize_denormalization_fields()

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
def load_test_data():
    ingest_fixtures()
    total_sync_with_s3()


@task
def add_permissions_groups():
    """
    Add permissions groups for admin panel
    """
    # add capapi groups
    management.call_command('loaddata', 'capapi/fixtures/groups.yaml')


@task
def bag_jurisdiction(name):
    """ Write a BagIt package of all cases in a given jurisdiction. E.g. fab bag_jurisdiction:Ill. """
    jurisdiction = Jurisdiction.objects.get(name=name)
    export.export_cases_by_jurisdiction.delay(jurisdiction.pk)

@task
def bag_reporter(reporter_id):
    """ Write a BagIt package of all cases in a given reporter. E.g. `fab bag_reporter:137 """
    export.export_cases_by_reporter.delay(reporter_id)

@task
def bag_all_cases(before_date=None):
    """
        Export cases for all jurisdictions and reporters.
        If before_date is provided, only export targets where the export_date for the last export is less than before_date.
    """
    export.export_all(before_date)

@task
def bag_all_reporters(name):
    """ Write a BagIt package of all cases in a given reporter. E.g. `fab bag_jurisdiction:Illinois Appellate Court Reports """
    export.export_cases_by_reporter.delay(name)

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
    except:
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
    except:
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
        except:
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
def fix_jurisdictions():
    """
        Finds cases where the XML jurisdiction value is different from the text in the jurisdiction table and fixes it.
    """
    @shared_task
    def update_xml_jurisdiction(case_xml_id, orig_xml, jurisdiction, case_id):
        parsed = parse_xml(orig_xml)
        print("Updating {} to {} in {}".format(parsed('case|court')[0].get("jurisdiction"), jurisdiction, case_id))
        parsed('case|court')[0].set("jurisdiction", jurisdiction)
        CaseXML.objects.filter(pk=case_xml_id).update(orig_xml=force_str(serialize_xml(parsed)))

    query = """SELECT x.id, x.orig_xml, j.name_long, m.case_id from capdb_casexml x
    inner join capdb_casemetadata m on x.metadata_id = m.id
    inner join capdb_jurisdiction j on m.jurisdiction_id = j.id
    where text((ns_xpath('//case:court/@jurisdiction', x.orig_xml))[1]) != text(j.name_long)"""

    with connections['capdb'].cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()
        while row is not None:
            case_xml_id = row[0]
            orig_xml = row[1]
            jurisdiction = row[2]
            case_id = row[3]
            update_xml_jurisdiction(case_xml_id, orig_xml, jurisdiction, case_id)
            row = cursor.fetchone()


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
    pathlib.Path(out_path).write_text(data)


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
        Download all PDFs, or all for a jurisdiction, to writeable_download_files_storage.
        Locally, this is the same as download_files_storage, but will differ in production,
        as we're using a read-only overlay to expose the files.
    """
    from capdb.storages import pdf_storage, writeable_download_files_storage
    from pathlib import Path
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
            if not writeable_download_files_storage.exists(str(new_path)):
                break
        else:
            raise Exception("Failed to find a non-existent path for %s" % new_path)

        try:
            # copy file
            try:
                copy_file(source_path, new_path, from_storage=pdf_storage, to_storage=writeable_download_files_storage)
            except IOError:
                print("  - ERROR: source file not found")
                continue

            # save PDF location on volume model
            volume.pdf_file.name = str(new_path)
            volume.save()
            print("  - Downloaded to %s" % new_path)
        except:
            # clean up partial downloads if process is killed
            writeable_download_files_storage.delete(str(new_path))
            raise


@task
def unredact_out_of_copyright_volumes(dry_run='true'):
    from django.utils import timezone
    key = None
    if dry_run == 'false':
        key = input("Enter decryption key: ").strip()
    volumes = (VolumeMetadata.objects
        .filter(out_of_scope=False, redacted=True, publication_year__lt=timezone.now().year-95)
        .select_related('reporter')
        .order_by('publication_year', 'volume_number'))
    for volume in volumes:
        print("Unredacting %s %s (%s)" % (volume.volume_number, volume.reporter.short_name, volume.publication_year))
        if dry_run == 'false':
            volume.unredact(key)


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


if __name__ == "__main__":
    # allow tasks to be run as "python fabfile.py task"
    # this is convenient for profiling, e.g. "kernprof -l fabfile.py refresh_case_body_cache"
    from fabric.main import main
    main()

