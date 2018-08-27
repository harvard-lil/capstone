import csv
import glob
import gzip
import hashlib
import os
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

from django.db import connections
from django.utils.encoding import force_str
from django.conf import settings
from fabric.api import local
from fabric.decorators import task

from capapi.models import CapUser
from capdb.models import VolumeXML, VolumeMetadata, CaseXML, SlowQuery, Court, Jurisdiction

import capdb.tasks as tasks
# from process_ingested_xml import fill_case_page_join_table
from scripts import set_up_postgres, ingest_tt_data, data_migrations, ingest_by_manifest, mass_update, \
    validate_private_volumes as validate_private_volumes_script, compare_alto_case, export
from scripts.helpers import parse_xml, serialize_xml, court_name_strip, court_abbreviation_strip, copy_file, resolve_namespace


@task(alias='run')
def run_django(port="127.0.0.1:8000"):
    local("python manage.py runserver %s" % port)

@task
def test():
    """ Run tests with coverage report. """
    local("pytest --fail-on-template-vars --cov --cov-report=")

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
def init_db():
    """
        Set up new dev database.
    """
    migrate()

    print("Creating DEV admin user:")
    CapUser.objects.create_superuser('admin@example.com', 'admin')

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

        volume_barcode, case_number = barcode.split('_')

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
    volume_barcodes = [os.path.basename(d).split('_')[0] for d in
                glob.glob(os.path.join(settings.BASE_DIR, 'test_data/from_vendor/*'))]

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
    export.export_cases_by_jurisdiction(name)

@task
def bag_reporter(name):
    """ Write a BagIt package of all cases in a given reporter. E.g. `fab bag_jurisdiction:Illinois Appellate Court Reports """
    export.export_cases_by_reporter(name)

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
def show_slow_queries():
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
        heading = "*capstone slow query report for %s*" % datetime.now().strftime("%Y-%m-%d")
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
        init_db()
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
def fix_court_names():

    def update_cases(old_court_entry, stripped_name, stripped_abbrev, new_court_entry = None):
        for case_metadata in old_court_entry.case_metadatas.all():
            case = case_metadata.case_xml
            parsed = parse_xml(case.orig_xml)
            parsed('case|court')[0].set("abbreviation", stripped_abbrev)
            parsed('case|court')[0].text = stripped_name
            if new_court_entry is not None:
                case_metadata.court = new_court_entry
                case_metadata.save()
            case.orig_xml = serialize_xml(parsed)
            case.save(create_or_update_metadata=False)


    for court in Court.objects.all():
        stripped_name = court_name_strip(court.name)
        stripped_abbrev = court_abbreviation_strip(court.name_abbreviation)

        if court.name != stripped_name or court.name_abbreviation != stripped_abbrev:

            # see if there are any entries which already have the correct court name/abbr/jur
            similar_courts = Court.objects.order_by('slug')\
                .prefetch_related('case_metadatas__case_xml')\
                .filter(name=stripped_name, name_abbreviation=stripped_abbrev, jurisdiction=court.jurisdiction)

            # if so, set the court entry this court's cases to the correct court, and delete this court
            # We are assuming that the first entry, organized by slug, is the correct one.
            if similar_courts.count() > 0:
                update_cases(court, stripped_name, stripped_abbrev, similar_courts[0])

                # we delete the court once we confirm that there are no more cases associated with it
                if len(court.case_metadatas.all()) == 0:
                    court.delete()
                else:
                    raise Exception('{} case(s) not moved from court "{}" ("{}") to "{}" ("{}").'
                                    .format(court.case_metadatas.count(), court.name, court.name_abbreviation,
                                            similar_courts[0].name, similar_courts[0].name_abbreviation))

            # If there are no other similar courts, let's correct this name and cases
            else:
                court.name = stripped_name
                court.name_abbreviation = stripped_abbrev
                court.save()
                update_cases(court, stripped_name, stripped_abbrev)


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
                if current_vol.split("_", 1)[0] != next_vol.split("_", 1)[0]:
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
