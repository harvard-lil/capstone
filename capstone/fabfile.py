import csv
import glob
import gzip
import hashlib
import os
import pathlib
from datetime import datetime
import django
import json
from random import randrange, randint
from pathlib import Path
from celery import shared_task, group

# set up Django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception as e:
    print("WARNING: Can't configure Django -- tasks depending on Django will fail:\n%s" % e)

from django.core import management
from django.db import connections
from django.utils.encoding import force_str
from django.conf import settings
from fabric.api import local
from fabric.decorators import task

from capapi.models import CapUser
from capdb.models import VolumeXML, VolumeMetadata, CaseXML, SlowQuery, Jurisdiction, Reporter

import capdb.tasks as tasks
from scripts import set_up_postgres, ingest_tt_data, data_migrations, ingest_by_manifest, mass_update, \
    validate_private_volumes as validate_private_volumes_script, compare_alto_case, export, count_chars
from scripts.helpers import parse_xml, serialize_xml, copy_file, resolve_namespace, volume_barcode_from_folder


@task(alias='run')
def run_django(port="127.0.0.1:8000"):
    local("python manage.py runserver %s" % port)

@task
def test():
    """ Run tests with coverage report. """
    local("pytest --fail-on-template-vars --cov --cov-report=")

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

@task
def ingest_jurisdiction():
    ingest_tt_data.populate_jurisdiction()

@task
def ingest_metadata():
    ingest_tt_data.populate_jurisdiction()
    ingest_tt_data.ingest(False)

@task
def sync_metadata():
    """
    Takes data from tracking tool db and translates them to the postgres db.
    Changes field names according to maps listed at the top of ingest_tt_data script.
    """
    ingest_tt_data.ingest(True)

@task
def relink_reporter_jurisdiction():
    """
    This will re-build the links between the Reporter table and Jurisdiction table
    """
    ingest_tt_data.relink_reporter_jurisdiction()

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
def rename_tags_from_json_id_list(json_path, tag=None):
    with open(os.path.abspath(os.path.expanduser(json_path))) as data_file:    
        parsed_json = json.load(data_file)
    mass_update.rename_casebody_tags_from_json_id_list(parsed_json, tag)

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

    local("python manage.py migrate --database=default")
    local("python manage.py migrate --database=capdb")
    if settings.USE_TEST_TRACKING_TOOL_DB:
        local("python manage.py migrate --database=tracking_tool")

    update_postgres_env()

@task
def load_test_data():
    if settings.USE_TEST_TRACKING_TOOL_DB:
        local("python manage.py loaddata --database=tracking_tool test_data/tracking_tool.json")
    ingest_metadata()
    ingest_jurisdiction()
    total_sync_with_s3()


@task
def add_permissions_groups():
    """
    Add permissions groups for admin panel
    """
    # add capapi groups
    local("python manage.py loaddata capapi/fixtures/groups.yaml")


@task
def validate_casemets_alto_link(sample_size=100000):
    """
    Will test a random sample of cases.
    Tests 100,000 by default, but you can specify a sample set size on the command line. For example, to test 14 cases:
    fab validate_casemets_alto_link:14
    """
    sample_size = int(sample_size) if int(sample_size) < CaseXML.objects.all().count() else CaseXML.objects.all().count()
    tested = []
    while len(tested) < sample_size:
        try:
            key = randrange(1, CaseXML.objects.last().id + 1)
            while key in tested:
                key = randrange(1, CaseXML.objects.last().id + 1)
            tested.append(key)
            case_xml = CaseXML.objects.get(pk=key)
            print(compare_alto_case.validate(case_xml))
        except CaseXML.DoesNotExist:
            continue
    print("Tested these CaseXML IDs:")
    print(tested)



@task
def add_test_case(*barcodes):
    """
        Write test data and fixtures for given volume and case. Example: fab add_test_case:32044057891608_0001

        NOTE:
            DATABASES['tracking_tool'] must point to real tracking tool db.
            STORAGES['ingest_storage'] must point to real harvard-ftl-shared.

        Output is stored in test_data/tracking_tool.json and test_data/from_vendor.
        Tracking tool user details are anonymized.
    """

    from django.core import serializers
    from tracking_tool.models import Volumes, Reporters, BookRequests, Pstep, Eventloggers, Hollis, Users
    from capdb.storages import ingest_storage

    ## write S3 files to local disk

    for barcode in barcodes:

        print("Writing data for", barcode)

        volume_barcode, case_number = barcode.rsplit('_', 1)

        # get volume dir
        source_volume_dirs = list(ingest_storage.iter_files(volume_barcode, partial_path=True))
        if not source_volume_dirs:
            print("ERROR: Can't find volume %s. Skipping!" % volume_barcode)
        source_volume_dir = sorted(source_volume_dirs, reverse=True)[0]

        # make local dir
        dest_volume_dir = os.path.join(settings.BASE_DIR, 'test_data/from_vendor/%s' % os.path.basename(source_volume_dir))
        os.makedirs(dest_volume_dir, exist_ok=True)

        # copy volume-level files
        for source_volume_path in ingest_storage.iter_files(source_volume_dir):
            dest_volume_path = os.path.join(dest_volume_dir, os.path.basename(source_volume_path))
            if '.' in os.path.basename(source_volume_path):
                # files
                copy_file(source_volume_path, dest_volume_path, from_storage=ingest_storage)
            else:
                # dirs
                os.makedirs(dest_volume_path, exist_ok=True)

        # read volmets xml
        source_volmets_path = glob.glob(os.path.join(dest_volume_dir, '*.xml'))[0]
        with open(source_volmets_path) as volmets_file:
            volmets_xml = parse_xml(volmets_file.read())

        # copy case file and read xml
        source_case_path = volmets_xml.find('mets|file[ID="casemets_%s"] > mets|FLocat' % case_number).attr(resolve_namespace('xlink|href'))
        source_case_path = os.path.join(source_volume_dir, source_case_path)
        dest_case_path = os.path.join(dest_volume_dir, source_case_path[len(source_volume_dir)+1:])
        copy_file(source_case_path, dest_case_path, from_storage=ingest_storage)
        with open(dest_case_path) as case_file:
            case_xml = parse_xml(case_file.read())

        # copy support files for case
        for flocat_el in case_xml.find('mets|FLocat'):
            source_path = os.path.normpath(os.path.join(os.path.dirname(source_case_path), flocat_el.attrib[resolve_namespace('xlink|href')]))
            dest_path = os.path.join(dest_volume_dir, source_path[len(source_volume_dir) + 1:])
            copy_file(source_path, dest_path, from_storage=ingest_storage)

        # remove unused files from volmets
        local_files = glob.glob(os.path.join(dest_volume_dir, '*/*'))
        local_files = [x[len(dest_volume_dir)+1:] for x in local_files]
        for flocat_el in volmets_xml.find('mets|FLocat'):
            if not flocat_el.attrib[resolve_namespace('xlink|href')] in local_files:
                file_el = flocat_el.getparent()
                file_el.getparent().remove(file_el)
        with open(source_volmets_path, "wb") as out_file:
            out_file.write(serialize_xml(volmets_xml))

    ## load metadata into JSON fixtures from tracking tool

    to_serialize = set()
    user_ids = set()
    volume_barcodes = [
        volume_barcode_from_folder(os.path.basename(d)) for d in
        glob.glob(os.path.join(settings.BASE_DIR, 'test_data/from_vendor/*'))
    ]

    for volume_barcode in volume_barcodes:

        print("Updating metadata for", volume_barcode)

        try:
            tt_volume = Volumes.objects.get(bar_code=volume_barcode)
        except Volumes.DoesNotExist:
            raise Exception("Volume %s not found in the tracking tool -- is settings.py configured to point to live tracking tool data?" % volume_barcode)
        to_serialize.add(tt_volume)

        user_ids.add(tt_volume.created_by)

        tt_reporter = Reporters.objects.get(id=tt_volume.reporter_id)
        to_serialize.add(tt_reporter)

        to_serialize.update(Hollis.objects.filter(reporter_id=tt_reporter.id))

        request = BookRequests.objects.get(id=tt_volume.request_id)
        request.from_field = request.recipients = 'example@example.com'
        to_serialize.add(request)

        for event in Eventloggers.objects.filter(bar_code=tt_volume.bar_code):
            if not event.updated_at:
                event.updated_at = event.created_at
            to_serialize.add(event)
            user_ids.add(event.created_by)
            if event.pstep_id:
                pstep = Pstep.objects.get(step_id=event.pstep_id)
                to_serialize.add(pstep)

    for i, user in enumerate(Users.objects.filter(id__in=user_ids)):
        user.email = "example%s@example.com" % i
        user.password = 'password'
        user.remember_token = ''
        to_serialize.add(user)

    serializer = serializers.get_serializer("json")()
    with open(os.path.join(settings.BASE_DIR, "test_data/tracking_tool.json"), "w") as out:
        serializer.serialize(to_serialize, stream=out, indent=2)

    ## update inventory files
    write_inventory_files()

@task
def bag_jurisdiction(name):
    """ Write a BagIt package of all cases in a given jurisdiction. E.g. fab bag_jurisdiction:Ill. """
    jurisdiction = Jurisdiction.objects.get(name=name)
    export.export_cases_by_jurisdiction.delay(jurisdiction.pk)

@task
def bag_reporter(name):
    """ Write a BagIt package of all cases in a given reporter. E.g. `fab bag_jurisdiction:Illinois Appellate Court Reports """
    reporter = Reporter.objects.get(full_name=name)
    export.export_cases_by_reporter.delay(reporter.pk)

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

        queries.append({
            'fallback': saved_query.label or query,
            'title': "%d call%s, %.1f ms, %.1f ms/query" % (
                call_count, "" if call_count == 1 else "s", run_time, run_time/float(call_count)
            ),
            'text': saved_query.label or "```%s```" % query
        })
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
    It might be a good idea to:
        1. point tracking_tool to prod (WARNING: you are dealing with prod data be very very careful!)
        2. go to ingest_tt_data.py's `ingest` method and comment out all
            copyModel statements except
            `copyModel(Reporters, Reporter, reporter_field_map, dupcheck)`
            since Reporter is required for populating jurisdictions

        3. run `fab ingest_metadata`
        4. remove pointer to prod tracking_tool db!!
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
def create_case_text_for_all_cases(update_existing=False):
    update_existing = True if update_existing else False
    tasks.create_case_text_for_all_cases(update_existing=update_existing)

@task
def count_chars_in_all_cases(path="/tmp/counts"):
    count_chars.count_chars_in_all_cases(path)


@task
def ngram_jurisdictions(replace_existing=False):
    """ Generate ngrams for all jurisdictions. If replace_existing is False (default), only jurisdiction-years without existing ngrams will be indexed. """
    from scripts.ngrams import ngram_jurisdictions
    ngram_jurisdictions(replace_existing=bool(replace_existing))


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
def report_multiple_jurisdictions(out_path="court_jurisdictions.csv"):
    """
        Write a CSV report of courts with multiple jurisdictions.
    """
    from capweb.helpers import select_raw_sql
    from tqdm import tqdm

    # select distinct cm.court_id from capdb_casemetadata cm, capdb_court c where cm.court_id=c.id and c.jurisdiction_id != cm.jurisdiction_id;
    court_ids = {
    8770, 8775, 8797, 8802, 8805, 8815, 8818, 8823, 8826, 8829, 8832, 8840, 8847, 8847, 8864, 8894, 8910, 8910, 8933,
    8944, 8954, 8962, 8973, 8977, 8978, 8978, 8981, 8991, 8991, 8992, 9000, 9004, 9009, 9016, 9018, 9020, 9021, 9022,
    9026, 9027, 9029, 9034, 9039, 9041, 9044, 9045, 9048, 9049, 9051, 9056, 9058, 9059, 9062, 9063, 9065, 9066, 9068,
    9071, 9074, 9076, 9081, 9081, 9083, 9085, 9086, 9089, 9092, 9094, 9099, 9103, 9104, 9104, 9107, 9112, 9114, 9130,
    9131, 9132, 9138, 9138, 9141, 9148, 9149, 9153, 9158, 9181, 9198, 9200, 9204, 9212, 9223, 9223, 9225, 9229, 9252,
    9266, 9270, 9274, 9297, 9302, 9310, 9311, 9318, 9328, 9341, 9353, 9358, 9385, 9386, 9388, 9389, 9395, 9424, 9426,
    9429, 9434, 9434, 9444, 9444, 9447, 9455, 9465, 9480, 9485, 9494, 9509, 9509, 9511, 9511, 9511, 9513, 9524, 9534,
    9540, 9549, 9551, 9554, 9620, 9708, 9725, 9805, 9846, 9874, 9892, 9906, 9907, 9929, 9948, 9976, 9999, 10006, 10076,
    10101, 10108, 10111, 10117, 10152, 10152, 10179, 10312, 10363, 10451, 10497, 10597, 10888, 11154, 11211, 11274,
    11277, 11613, 11696, 11757, 11860, 11887, 11933, 11933, 11942, 11944, 11969, 11976, 11985, 11987, 11987, 12083,
    12104, 12136, 12997, 13048, 13076, 13083, 13093, 13097, 13100, 13104, 13132, 13148, 13205, 13326, 13390, 13393,
    13428, 13438, 13543, 13543, 13565, 13570, 13797, 14005, 14156, 14236, 14272, 14337, 14473, 14476, 14477, 14490,
    14607, 14978, 14986, 15006, 15006, 15007, 15016, 15201, 15300, 15344, 15741, 15767, 16436, 16657, 16681, 16686,
    17013, 17111, 17229, 17308, 17319, 17329, 17329, 17627, 18775, 18961, 18968, 20164}
    with open(out_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        for court_id in tqdm(court_ids):
            rows = select_raw_sql("select count(m), jurisdiction_slug, court_name, court_slug "
                                  "from capdb_casemetadata m where court_id=%s "
                                  "group by jurisdiction_slug, court_name, court_slug",
                                  [court_id], using='capdb')
            csv_writer.writerow([rows[0].court_name])
            for row in rows:
                url = "https://api.case.law/v1/cases/?court=%s&jurisdiction=%s" % (row.court_slug, row.jurisdiction_slug)
                csv_writer.writerow([row.jurisdiction_slug, row.count, url])


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

    from tqdm import tqdm

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
