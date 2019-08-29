from datetime import datetime
from time import sleep

from celery import shared_task
from celery.exceptions import Reject
from django.db import connections
from django.db.models import Prefetch
from django.utils import timezone
from elasticsearch import ElasticsearchException
from elasticsearch.helpers import BulkIndexError

from capapi.documents import CaseDocument
from scripts.helpers import ordered_query_iterator

from capdb.models import *


### HELPERS ###

def run_task_for_volumes(task, volumes=None, last_run_before=None, **kwargs):
    """
        Run the given celery task for the given queryset of volumes, or all volumes if not specified.
        If last_run_before is provided as an ISO timestamp, volumes will only be run if volume.task_statuses indicates that
        the task has not succeeded after that time.
    """
    if volumes is None:
        volumes = VolumeMetadata.objects.all()
    if last_run_before:
        volumes = volumes.exclude(**{
            "task_statuses__%s__success" % task.name: True,
            "task_statuses__%s__timestamp__gte" % task.name: last_run_before
        })
    for volume_id in volumes.values_list('pk', flat=True):
        task.delay(volume_id, **kwargs)

@contextmanager
def record_task_status_for_volume(task, volume_id):
    """
        Context manager to record in volume.task_statuses whether the given task succeeds or fails.
    """
    try:
        yield
    except Exception as e:
        volume = VolumeMetadata.objects.get(pk=volume_id)
        volume.task_statuses[task.name] = {
            'timestamp': timezone.now().isoformat(),
            'error': str(e),
        }
        volume.save()
        raise
    else:
        volume = VolumeMetadata.objects.get(pk=volume_id)
        volume.task_statuses[task.name] = {
            'timestamp': timezone.now().isoformat(),
            'success': True,
        }
        volume.save()

### TASKS ###

@shared_task(bind=True, acks_late=True)  # use acks_late for tasks that can be safely re-run if they fail
def update_in_scope_for_vol(self, volume_id):
    """
        Call .update_in_scope() for all cases in given volume.
    """
    with record_task_status_for_volume(self, volume_id):
        CaseMetadata.objects.filter(volume_id=volume_id).update_in_scope()


@shared_task(bind=True, acks_late=True)  # use acks_late for tasks that can be safely re-run if they fail
def update_elasticsearch_for_vol(self, volume_id):
    """
        Index all cases for given volume with elasticsearch.
    """
    with record_task_status_for_volume(self, volume_id):
        # fetch cases
        cases = (CaseMetadata.objects
            .in_scope()
            .filter(volume_id=volume_id)
            .select_related('volume', 'reporter', 'court', 'jurisdiction', 'reporter', 'body_cache')
            .exclude(body_cache=None))

        # attempt to store 10 times, with linearly increasing backoff. this gives time for the bulk queue to be processed
        # if necessary (in which case we'll get BulkIndexError with error 429, too many requests).
        for i in range(10):
            try:
                CaseDocument().update(cases)
                VolumeMetadata.objects.filter(pk=volume_id).update(last_es_index=timezone.now())
                return
            except ElasticsearchException as e:
                if i == 9:
                    # If all 10 requests fail, re-add job to the back of the queue
                    if type(e) == BulkIndexError:
                        # delete submitted data from BulkIndexError, because otherwise error messages are too large to store
                        for item in e.args[1]:
                            for v in item.values():
                                v['data'] = '[data omitted]'
                    raise Reject('Bulk indexing of volume %s failed: %s' % (volume_id, e), requeue=True)
                sleep(i)


@shared_task(bind=True, acks_late=True)  # use acks_late for tasks that can be safely re-run if they fail
def sync_from_initial_metadata_for_vol(self, volume_id, force):
    """
        call sync_from_initial_metadata on cases in given volume
    """
    with record_task_status_for_volume(self, volume_id):
        cases = (CaseMetadata.objects
            .filter(volume_id=volume_id)
            .select_related('structure', 'initial_metadata', 'volume')
            .exclude(initial_metadata=None)
            .exclude(structure=None))
        for c in cases:
            c.sync_from_initial_metadata(force=force)


@shared_task
def sync_case_body_cache_for_vol(volume_id, rerender=True):
    """
        call sync_case_body_cache on cases in given volume
    """
    volume = VolumeMetadata.objects.get(pk=volume_id)
    pages = list(volume.page_structures.all())
    blocks_by_id = PageStructure.blocks_by_id(pages)
    fonts_by_id = CaseFont.fonts_by_id(blocks_by_id)
    labels_by_block_id = PageStructure.labels_by_block_id(pages)

    query = volume.case_metadatas\
        .select_related('structure', 'body_cache')\
        .defer('body_cache__html', 'body_cache__xml', 'body_cache__text', 'body_cache__json')

    for case_metadata in query:
        case_metadata.sync_case_body_cache(blocks_by_id, fonts_by_id, labels_by_block_id, rerender=rerender)


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
        Call create_case_text for each volume
    """
    run_task_for_volumes(create_case_text, update_existing=update_existing)


@shared_task
def create_case_text(volume_id, update_existing=False):
    """
        Create or update cases for each volume
    """
    cases = CaseMetadata.objects \
        .in_scope() \
        .order_by('id') \
        .filter(volume_id=volume_id) \
        .select_related('case_xml', 'case_text')

    if not update_existing:
        cases = cases.filter(case_text=None)

    for case in ordered_query_iterator(cases):
        case.create_or_update_case_text()


def retrieve_images_from_all_cases(update_existing=False):
    """
        Call celery task to get images for each volume
    """
    run_task_for_volumes(retrieve_images_from_cases, update_existing=update_existing)


@shared_task(bind=True, acks_late=True)  # use acks_late for tasks that can be safely re-run if they fail
@transaction.atomic(using='capdb')
def retrieve_images_from_cases(self, volume_id, update_existing=True):
    """
        Create or update case images for each volume
    """
    with record_task_status_for_volume(self, volume_id):
        cases = CaseMetadata.objects.filter(volume_id=volume_id) \
            .only('body_cache__html') \
            .order_by('id') \
            .select_related('body_cache') \
            .prefetch_related(Prefetch('caseimages', queryset=CaseImage.objects.only('hash', 'case'))) \
            .exclude(body_cache=None) \
            .filter(body_cache__html__contains='<img') \
            .select_for_update()

        if not update_existing:
            cases = cases.exclude(caseimages__isnull=False)

        for case in cases:
            case.retrieve_and_store_images()
