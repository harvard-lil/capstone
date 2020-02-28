import re
import csv
from copy import copy
from datetime import datetime
from time import sleep
from celery import shared_task
from celery.exceptions import Reject
from elasticsearch import ElasticsearchException
from elasticsearch.helpers import BulkIndexError
from urllib3.exceptions import ReadTimeoutError
from reporters_db import REPORTERS, VARIATIONS_ONLY
from collections import deque

from django.db import connections
from django.db.models import Prefetch, Q
from django.utils import timezone

from capapi.documents import CaseDocument
from capdb.models import *

### HELPERS ###

def run_task_for_volumes(task, volumes=None, last_run_before=None, synchronous=False, **kwargs):
    """
        Run the given celery task for the given queryset of volumes, or all volumes if not specified.
        If last_run_before is provided as an ISO timestamp, volumes will only be run if volume.task_statuses indicates that
        the task has not succeeded after that time.
    """
    if volumes is None:
        volumes = VolumeMetadata.objects.all()
    if last_run_before:
        volumes = volumes.exclude(**{
            "task_statuses__%s__has_key" % task.name: "success",
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

@shared_task(bind=True, acks_late=True)
def remove_id_number_in_volume(self, volume_id):
    # patterns to replace
    regexes = [
        # a-number
        r'\bA *[-—] *\d{8,9}\b',
        r'\bA\d{8,9}\b',
        # ssn
        r'\b\d{3} *[-—] *\d{2} *[-—] *\d{4}\b',
        r'\b\d{3} +\d{2} +\d{4}\b',
    ]

    # database filter for text matching any of those patterns
    filters = Q()
    for regex in regexes:
        postgres_regex = regex.replace(r'\b', r'\y')  # postgres uses \y instead of \b for boundaries
        filters |= Q(name__regex=postgres_regex) | Q(body_cache__text__regex=postgres_regex)
    cases = (CaseMetadata.objects
                 .filter(filters, volume_id=volume_id)
                 .select_related('body_cache')
                 .only('body_cache__text'))

    # set no_index_redacted for each matching case
    with record_task_status_for_volume(self, volume_id):
        for case in cases:
            replacement = copy(case.no_index_redacted) if case.no_index_redacted else {}
            for regex in regexes:
                for match in set(re.findall(regex, case.body_cache.text + case.name)):
                    if match in replacement:
                        continue
                    replacement[match] = re.sub(r'\d', 'X', match)
            if replacement != case.no_index_redacted:
                case.no_index_redacted = replacement
                case.save()


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
            .select_related('volume', 'reporter', 'court', 'jurisdiction', 'body_cache')
            .exclude(body_cache=None))

        # attempt to store 10 times, with linearly increasing backoff. this gives time for the bulk queue to be processed
        # if necessary (in which case we'll get BulkIndexError with error 429, too many requests).
        for i in range(10):
            try:
                CaseDocument().update(cases)
                VolumeMetadata.objects.filter(pk=volume_id).update(last_es_index=timezone.now())
                return
            except (ElasticsearchException, ReadTimeoutError) as e:
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


@shared_task(bind=True, acks_late=True)  # use acks_late for tasks that can be safely re-run if they fail
def sync_case_body_cache_for_vol(self, volume_id, rerender=True):
    """
        call sync_case_body_cache on cases in given volume
    """
    with record_task_status_for_volume(self, volume_id):
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


@shared_task(bind=True, acks_late=True)  # use acks_late for tasks that can be safely re-run if they fail
def sync_xml_image_case_body_cache_for_vol(self, volume_id, rerender=True):
    """
        One-off to call sync_case_body_cache on cases in given volume only if they contain images,
        because images were previously missing from xml.
    """
    with record_task_status_for_volume(self, volume_id):
        volume = VolumeMetadata.objects.get(pk=volume_id)
        pages = list(volume.page_structures.all())
        blocks_by_id = PageStructure.blocks_by_id(pages)
        fonts_by_id = CaseFont.fonts_by_id(blocks_by_id)
        labels_by_block_id = PageStructure.labels_by_block_id(pages)

        query = (volume.case_metadatas
            .filter(body_cache__html__contains='<img')
            .select_related('structure', 'body_cache')
            .defer('body_cache__html', 'body_cache__xml', 'body_cache__text', 'body_cache__json')
         )

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


@shared_task(bind=True, acks_late=True)
def extract_citations_per_vol(self, volume_id, update_existing=False):
    regex = "((?:\d\s?)+)\s+([0-9a-zA-Z][\s0-9a-zA-Z.']{0,40})\s+(\d+)"
    regex_filter = Q(body_cache__text__regex=regex)
    cases = (CaseMetadata.objects.filter(regex_filter, volume_id=volume_id)
             .select_related('body_cache')
             .only('body_cache__text'))
    misses = []
    # database filter for text matching any of those patterns
    # set no_index_redacted for each matching case
    with record_task_status_for_volume(self, volume_id):
        for case in cases:
            for match in set(re.findall(regex, case.body_cache.text + case.name)):
                vol_num, reporter_str, page_num = match
                citation = " ".join(match)
                cite, created = ExtractedCitation.objects.get_or_create(original_cite=citation)
                cite.case_origins.add(case.id)
                if created or update_existing:
                    # Try to find matching reporter instance in our DB
                    reporters_to_check = []
                    # Look for found reporter string in the official REPORTER dict
                    if reporter_str in REPORTERS:
                        reporters_to_check.append(reporter_str)
                        for rep_instance in REPORTERS[reporter_str]:
                            reporters_to_check += list(rep_instance['variations'].keys())

                    # If reporter string is not found
                    # try to find it in VARIATIONS dict (for nominative reporters and such)
                    elif reporter_str in VARIATIONS_ONLY:
                        reporters_to_check.append(reporter_str)
                        for variation in VARIATIONS_ONLY[reporter_str]:
                            reporters_to_check.append(variation)
                            if variation in REPORTERS:
                                for rep_instance in REPORTERS[variation]:
                                    reporters_to_check += list(rep_instance['variations'].keys())
                    else:
                        misses.append(match)
                    reporter = find_reporter_match(reporter_str, reporters_to_check)
                    if reporter:
                        cite.reporter_match = reporter
                        try:
                            cite.volume_match = VolumeMetadata.objects.get(
                                reporter=reporter,
                                volume_number=vol_num
                            )
                        except VolumeMetadata.DoesNotExist:
                            pass

            cite.reporter_original_string = reporter_str
            cite.volume_original_number = vol_num
            cite.page_original_number = page_num
            try:
                # try to get original citation
                cite.citation_match = Citation.objects.get(cite=citation)
            except Citation.DoesNotExist:
                # try to get citation with reporter match
                if cite.reporter_match:
                    try:
                        official_cite_guess = "%s %s %s" % (vol_num, cite.reporter_match, page_num)
                        cite.citation_match = Citation.objects.get(official_cite_guess)
                    except Citation.DoesNotExist:
                        pass
                pass
            cite.save()

    fieldnames = ['volume_id', 'reporter_str', 'vol_num', 'page_num']
    # TODO: figure out where to put missed citations csv
    with open("missed_citations.csv", "a+") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        [writer.writerow({"volume_id": volume_id, "reporter_str": reporter_str, "vol_num": vol_num, "page_num": page_num}) for case in cases]


def find_reporter_match(reporter_str, remaining_list_to_check):
    remaining_list_to_check = deque(remaining_list_to_check)
    reporters = Reporter.objects.filter(short_name=reporter_str)
    if reporters.count() == 0:
        if len(remaining_list_to_check):
            new_reporter_str =remaining_list_to_check.popleft()
            find_reporter_match(new_reporter_str, remaining_list_to_check)
        else:
            return
    elif reporters.count() == 1:
        return reporters[0]
    else:
        # Too many reporters found, return no reporters
        return
