import os
import json
from datetime import datetime
from celery import shared_task

from django.db import connection, transaction

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
def count_courts(file_name='court_count.json', file_dir='capapi/data/', write_to_file=True):
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
def count_reporters_and_volumes(file_name='reporter_count.json', file_dir='capapi/data/', write_to_file=True):
    file_path = os.path.join(file_dir, file_name)
    results = {
        'totals': {
            'total': 0,
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
            results[jur]['total'] += 1
            results[jur]['reporters'].append(full_name)
            if volume_count:
                results[jur]['volume_count'] += volume_count

        else:
            results[jur] = {'total': 1}
            results[jur]['start_year'] = res[1]
            results[jur]['reporters'] = [full_name]
            results[jur]['volume_count'] = volume_count
            old_jur = jur

        if volume_count:
            results['totals']['volume_count'] += volume_count
        if start_year in results:
            results['totals'][start_year]['volume_count'] += volume_count
            results['totals'][start_year]['total'] += 1
        else:
            results['totals'][start_year] = {'volume_count': volume_count, 'total': 1}

    results['totals']['total'] = len(reps)
    results['recorded'] = str(datetime.now())

    if not write_to_file:
        return results

    with open(file_path, "w+") as f:
        json.dump(results, f)
    print('done counting reporters')


@shared_task
def count_cases(file_name='case_count.json', file_dir='capapi/data', write_to_file=True):
    file_path = os.path.join(file_dir, file_name)
    results = {'totals': {'total': 0}}
    with connection.cursor() as cursor:
        cursor.execute("select jurisdiction_id, extract(year from decision_date)::integer as case_year, count(*) from capdb_casemetadata where duplicative=false group by jurisdiction_id, case_year;")
        db_results = cursor.fetchall()

    for res in db_results:
        jur, case_year, count = res
        if jur not in results:
            results[jur] = {'total': count, case_year: count}
        else:
            results[jur][case_year] = count
            results[jur]['total'] += count

        if case_year in results['totals']:
            results['totals'][case_year] += count
        else:
            results['totals'][case_year] = count

        results['totals']['total'] += count

    results['recorded'] = str(datetime.now())

    if not write_to_file:
        return results

    with open(file_path, "w+") as f:
        json.dump(results, f)
    print('done counting cases')
