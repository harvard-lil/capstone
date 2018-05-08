import json
from datetime import datetime
from celery import shared_task

from django.db import connection, transaction
from django.db.models import Min, Max

from capdb.models import *
from capapi.models import CapData

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
def count_data(jurisdiction=None):
    # jurisdictions
    # reporters per jurisdiction
    # volumes per reporter
    # cases per volume?
    if jurisdiction:
        print("creating data for specific jurisdiction")
        return

    total_data, created = CapData.objects.get_or_create(slug='total')
    total_data.reset()
    jurisdictions = Jurisdiction.objects.all()
    for jur in jurisdictions:
        data, created = CapData.objects.get_or_create(slug=jur.slug)
        data.reset()
        reps = Reporter.objects.filter(jurisdictions=jur.id)
        data.reporters = reps.count()

        for rep in reps:
            vols = VolumeMetadata.objects.filter(reporter=rep.id)
            data.volumes = vols.count()
            for vol in vols:
                cases = vol.case_metadatas.filter(duplicative=False)
                data.cases = cases.count()
        data.save()
        total_data.cases += data.cases
        total_data.reporters += data.reporters
        total_data.volumes += data.volumes
        total_data.save()


@shared_task
def count_courts(file_path='capapi/data/court_count.json'):
    jurs = Jurisdiction.objects.all()
    results = {}
    total = 0
    for jur in jurs:
        court_count = Court.objects.filter(jurisdiction=jur).count()
        results[jur.slug] = court_count
        total += court_count
    results['total'] = total
    results['recorded'] = str(datetime.now())
    with open(file_path, 'w+') as f:
        json.dump(results, f)
    print('done counting courts')


@shared_task
def count_reporters(file_path='capapi/data/reporter_count.json'):
    jurs = Jurisdiction.objects.all()
    results = {}
    total = 0
    for jur in jurs:
        reporters = Reporter.objects.filter(jurisdictions=jur, start_year__isnull=False)\
            .order_by('start_year')
        total_volume_count = 0
        for rep in reporters:
            if rep.volume_count:
                total_volume_count += rep.volume_count
        rep_count = reporters.count()
        total += rep_count
        try:
            results[jur.slug] = {
                "count": rep_count,
                "first_year": reporters.aggregate(oldest=Min('start_year')),
                "last_year": reporters.aggregate(newest=Max('end_year')),
                "volume_count": total_volume_count
            }
        except:
            pass
    results["total"] = total
    results["recorded"] = str(datetime.now())
    with open(file_path, "w+") as f:
        json.dump(results, f)
    print('done counting reporters')


@shared_task
def count_cases(file_path='capapi/data/case_count.json'):
    results = {'total': 0}
    with connection.cursor() as cursor:
        cursor.execute("select jurisdiction_id, extract(year from decision_date)::integer as case_year, count(*) from capdb_casemetadata where duplicative=false group by jurisdiction_id, case_year;")

        db_results = cursor.fetchall()

    for res in db_results:
        if res[0] not in results:
            results[res[0]] = {res[1]: res[2]}
        else:
            results[res[0]][res[1]] = res[2]
        results['total'] += res[2]

    results["recorded"] = str(datetime.now())
    with open(file_path, "w+") as f:
        json.dump(results, f)
    print('done counting cases')

