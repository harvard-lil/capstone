from datetime import datetime
from celery import shared_task
from django.db import connections, transaction
from scripts.helpers import extract_casebody

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
        Allocate `ram` megabytes of ram and run `cpu` million additions.
    """
    print("Task %s" % i)
    # waste 0-ram MB of RAM
    waste_ram = bytearray(2**20 * ram)  # noqa

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
    with connections['capdb'].cursor() as cursor:
        new_xml_sql = "E'<?xml version=''1.0'' encoding=''utf-8''?>\n' || orig_xml"
        for table in ('capdb_casexml', 'capdb_pagexml'):
            print("Volume %s: updating %s" % (volume_id, table))
            update_sql = "UPDATE %(table)s SET orig_xml=xmlparse(CONTENT %(new_xml)s), md5=md5(%(new_xml)s) where volume_id = %%s and md5 is null" % {'table':table, 'new_xml':new_xml_sql}
            cursor.execute(update_sql, [volume_id])

@shared_task
def get_reporter_count_for_jur(jurisdiction_id):
    """
    Count reporters through the years per jurisdiction. Include totals.
    """
    if not jurisdiction_id:
        print('Must provide jurisdiction id')
        return

    with connections['capdb'].cursor() as cursor:
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

    with connections['capdb'].cursor() as cursor:
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
    results = {
        'recorded': str(datetime.now()),
        'total': jur.courts.count()
    }

    return results


def create_case_text_for_all_cases(update_existing=False):
    """
        iterate through all volumes, call celery task for each volume
    """
    query = CaseMetadata.objects.all()

    # if not updating existing, then only launch jobs for volumes with unindexed cases:
    if not update_existing:
        query = query.filter(case_text=None).distinct()

    # launch a job for each volume:
    for cmd_id in query.values_list('pk', flat=True):
        create_case_text.delay(cmd_id, update_existing=update_existing)


@shared_task
def create_case_text(case_id, update_existing=False):
    """
        create or update cases for each volume
    """
    case_metadata = CaseMetadata.objects.select_related('case_xml', 'case_text').get(pk=case_id)

    if not hasattr(case_metadata, 'case_text'):
        case_metadata.case_text = CaseText()
    elif not update_existing:
        return False

    case_metadata.case_text.text = extract_casebody(case_metadata.case_xml.orig_xml).text()
    case_metadata.case_text.save()

