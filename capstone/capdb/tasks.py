import os
import json
from datetime import datetime
from celery import shared_task

from django.db import connection, transaction
from django.conf import settings

from capdb.models import *


def create_case_metadata_from_all_vols(update_existing=False):
    """
        iterate through all volumes, call celery task for each volume
    """
    query = VolumeXML.objects.all()

    # if not updating existing, then only launch jobs for volumes with unindexed cases:
    if not update_existing:
        query = query.filter(case_xmls__metadata_id=None).distinct()

    # launch a job for each volume:
    for volume_id in query.values_list('pk', flat=True):
        create_case_metadata_from_vol.delay(volume_id, update_existing=update_existing)


@shared_task
def create_case_metadata_from_vol(volume_id, update_existing=False):
    """
        create or update cases for each volume
    """
    case_xmls = CaseXML.objects\
        .filter(volume_id=volume_id)\
        .select_related('metadata', 'volume__metadata__reporter')\
        .defer('orig_xml', 'volume__orig_xml')

    if not update_existing:
        case_xmls = case_xmls.filter(metadata_id=None)

    for case_xml in case_xmls:
        case_xml.create_or_update_metadata(update_existing=update_existing)


@shared_task
def update_volume_metadata(volume_xml_id):
    VolumeXML.objects.get(pk=volume_xml_id).update_metadata()


@shared_task
def test_slow(i, ram=10, cpu=30):
    """
        Waste a bunch of memory and CPU.
    """
    print("Task %s" % i)
    # waste 0-ram MB of RAM
    waste_ram = bytearray(2**20 * i%ram)  # noqa

    # waste CPU
    total = 0
    for i in range(cpu * 1000000):
        total += i


@shared_task
@transaction.atomic
def fix_md5_column(volume_id):
    """
        Our database has xml fields in the casexml and pagexml tables that are missing the <?xml> declaration, and that also don't have the md5 column filled.

        Here we update all the xml fields to add the <?xml> declaration and md5 hash.
    """
    with connection.cursor() as cursor:
        new_xml_sql = "E'<?xml version=''1.0'' encoding=''utf-8''?>\n' || orig_xml"
        for table in ('capdb_casexml', 'capdb_pagexml'):
            print("Volume %s: updating %s" % (volume_id, table))
            update_sql = "UPDATE %(table)s SET orig_xml=xmlparse(CONTENT %(new_xml)s), md5=md5(%(new_xml)s) where volume_id = %%s and md5 is null" % {'table':table, 'new_xml':new_xml_sql}
            cursor.execute(update_sql, [volume_id])


@shared_task
def count_courts(file_name='court_count.json', write_to_file=True):
    file_dir = settings.DATA_COUNT_DIR
    file_path = os.path.join(file_dir, file_name)
    jurs = Jurisdiction.objects.all()
    results = {'total': 0}
    for jur in jurs:
        court_count = jur.courts.count()
        results[jur.id] = court_count
        results['total'] += court_count

    results['recorded'] = str(datetime.now())

    if not write_to_file:
        return results

    with open(file_path, 'w+') as f:
        json.dump(results, f)
    print('done counting courts')


@shared_task
def count_reporters_and_volumes(file_name='reporter_and_volume_count.json', write_to_file=True):
    file_dir = settings.DATA_COUNT_DIR
    file_path = os.path.join(file_dir, file_name)
    results = {
        'totals': {
            'reporter_count': 0,
            'volume_count': 0
        }
    }

    with connection.cursor() as cursor:
        cursor.execute("select r.id, r.start_year, r.full_name, r.volume_count, j.jurisdiction_id as jurisdiction_id from capdb_reporter r join capdb_reporter_jurisdictions j on (r.id = j.reporter_id) order by j.jurisdiction_id, r.start_year;")
        db_results = cursor.fetchall()

    # make sure we don't count reporter in two jurisdictions twice
    reps = set()

    old_jur = db_results[0][4]
    for res in db_results:
        rep_id, start_year, full_name, volume_count, jur = res
        reps.add(rep_id)
        if jur == old_jur and jur in results:
            results[jur]['reporter_count'] += 1
            results[jur]['reporters'].append(full_name)
            if volume_count:
                results[jur]['volume_count'] += volume_count

        else:
            results[jur] = {'reporter_count': 1}
            results[jur]['start_year'] = res[1]
            results[jur]['reporters'] = [full_name]
            results[jur]['volume_count'] = volume_count
            old_jur = jur

        if volume_count:
            results['totals']['volume_count'] += volume_count
        if start_year in results:
            results['totals'][start_year]['volume_count'] += volume_count
            results['totals'][start_year]['reporter_count'] += 1
        else:
            results['totals'][start_year] = {'volume_count': volume_count, 'reporter_count': 1}

    results['totals']['reporter_count'] = len(reps)
    results['recorded'] = str(datetime.now())

    if not write_to_file:
        return results

    with open(file_path, "w+") as f:
        json.dump(results, f)
    print('done counting reporters')


@shared_task
def get_reporter_count_for_jur(jurisdiction_id):
    """
    Count reporters through the years per jurisdiction. Include totals.
    """
    if not jurisdiction_id:
        print('Must provide jurisdiction id')
        return

    with connection.cursor() as cursor:
        cursor.execute("select r.id, r.start_year, r.full_name, r.volume_count from capdb_reporter r join capdb_reporter_jurisdictions j on (r.id = j.reporter_id) where j.jurisdiction_id=%s order by r.start_year;" % jurisdiction_id)
        db_results = cursor.fetchall()

    results = {
        'total': 0,
        'years': {},
        'firsts': {
            'name': '',
            'id': ''
        }
    }

    try:
        results['firsts']['name'] = db_results[0][2]
        results['firsts']['id'] = db_results[0][0]
    except IndexError:
        pass

    for res in db_results:
        rep_id, start_year, full_name, volume_count = res
        if start_year in results:
            results['years'][start_year] += 1
        else:
            results['years'][start_year] = 1
        results['total'] += 1

    results['recorded'] = str(datetime.now())

    return results

@shared_task
def get_case_count_for_jur(jurisdiction_id):
    if not jurisdiction_id:
        print('Must provide jurisdiction id')
        return

    with connection.cursor() as cursor:
        cursor.execute("select extract(year from decision_date)::integer as case_year, count(*) from capdb_casemetadata where duplicative=false and jurisdiction_id=%s group by case_year;" % jurisdiction_id)
        db_results = cursor.fetchall()

    results = {
        'total': 0,
        'years': {},
        'firsts': {
            'name_abbreviation': '',
            'name': '',
            'id': ''
        }
    }

    first_case = CaseMetadata.objects.filter(jurisdiction_id=jurisdiction_id).order_by('decision_date').first()
    if first_case:
        results['firsts']['name_abbreviation'] = first_case.name_abbreviation
        results['firsts']['name'] = first_case.name
        results['firsts']['id'] = first_case.id

    for res in db_results:
        case_year, count = res
        results['years'][case_year] = count
        results['total'] += count

    results['recorded'] = str(datetime.now())
    return results


@shared_task
def get_court_count_for_jur(jurisdiction_id):
    if not jurisdiction_id:
        print("Must provide jurisdiction id")
        return

    jur = Jurisdiction.objects.get(id=jurisdiction_id)
    return jur.courts.count()


@shared_task
def get_counts_for_jur(jurisdiction_id):
    if not jurisdiction_id:
        print("Must provide jurisdiction id")
        return

    reporter_count = get_reporter_count_for_jur(jurisdiction_id)
    case_count = get_case_count_for_jur(jurisdiction_id)
    court_count = get_court_count_for_jur(jurisdiction_id)

    return {
        'reporter_count': reporter_count,
        'case_count': case_count,
        'court_count': court_count
    }


@shared_task
def get_case_totals_per_year(file_name="case_count.json", jurisdiction_id=None, write_to_file=True):
    jurs = [jurisdiction_id] if jurisdiction_id else list(Jurisdiction.objects.all().order_by('id').values_list('id', flat=True))
    results = {}
    years = range(1640, datetime.now().year+1)
    for jur in jurs:
        case_counts = get_case_count_for_jur(jur)
        for year in years:
            count_per_year = case_counts[year] if year in case_counts else 0
            if year not in results:
                results[year] = {jur: count_per_year}
            else:
                results[year][jur] = count_per_year

    if write_to_file:
        file_dir = settings.DATA_COUNT_DIR
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)
        file_path = os.path.join(file_dir, file_name)
        with open(file_path, 'w+') as f:
            json.dump(results, f)
    else:
        print(results)


@shared_task
def get_reporter_totals_per_year(jurisdiction_id=None, write_to_file=True):
    jurs = [jurisdiction_id] if jurisdiction_id else list(Jurisdiction.objects.all().order_by('id').values_list('id', flat=True))
    results = {}
    years = range(1640, datetime.now().year+1)
    for jur in jurs:
        reporter_counts = get_reporter_count_for_jur(jur)
        for year in years:
            str_year = str(year)
            count_per_year = reporter_counts[str_year] if str_year in reporter_counts else 0

            if str_year not in results:

                results[str_year] = {jur: count_per_year}
            else:
                results[str_year][jur] = count_per_year

    if write_to_file:
        file_dir = settings.DATA_COUNT_DIR
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)
        file_path = os.path.join(file_dir, "reporter_count.json")
        with open(file_path, 'w+') as f:
            json.dump(results, f)
    else:
        print(results)


def count_totals_per_year():
    cc_file_name = 'case_count.json'
    file_dir = settings.DATA_COUNT_DIR
    cc_file_path = os.path.join(file_dir, cc_file_name)
    file_name = 'case_totals_per_year.json'
    file_path = os.path.join(file_dir, file_name)
    with connection.cursor() as cursor:
        cursor.execute("select distinct extract(year from decision_date)::integer as case_year from capdb_casemetadata order by case_year;")
        years_results = cursor.fetchall()

    years = [year[0] for year in years_results]
    results = {'years': years}
    with open(cc_file_path, 'r') as f:
        case_counts = json.load(f)

    for jur_id in case_counts:
        if jur_id.isdigit():
            results[jur_id] = []
            recorded_years = case_counts[jur_id].keys()
            for year in years:
                # if year is not in recorded years, there were zero cases
                if str(year) not in recorded_years:
                    results[jur_id].append(0)
                else:
                    results[jur_id].append(case_counts[jur_id][str(year)])

    with open(file_path, 'w+') as f:
        json.dump(results, f)