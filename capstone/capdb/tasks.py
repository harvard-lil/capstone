import re
import csv
import json
from copy import copy
from datetime import datetime, timedelta
from string import ascii_lowercase
from time import sleep
from pathlib import Path

from celery import shared_task
from celery.exceptions import Reject
from elasticsearch import ElasticsearchException, NotFoundError
from elasticsearch.helpers import BulkIndexError
from urllib3.exceptions import ReadTimeoutError
from reporters_db import EDITIONS, VARIATIONS_ONLY
from django.db import connections
from django.db.models import Prefetch, Q
from django.utils import timezone
from collections import Counter

from capapi.documents import CaseDocument
from capapi.resources import cite_extracting_regex
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
        # find volumes where task has never run, or had an error, or had a success before last_run_before date
        volumes = volumes.filter(
            ~Q(task_statuses__has_key=task.name) |
            Q(**{"task_statuses__%s__has_key" % task.name: "error"}) |
            Q(**{
                "task_statuses__%s__has_key" % task.name: "success",
                "task_statuses__%s__timestamp__lt" % task.name: last_run_before
            })
        )
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
                case.robots_txt_until = timezone.now() + timedelta(days=7)
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
                 .filter(volume_id=volume_id)
                 .in_scope()
                 .select_related('volume', 'reporter', 'court', 'jurisdiction', 'body_cache')
                 .prefetch_related('extractedcitations', 'citations')
                 .exclude(body_cache=None))

        # attempt to store 10 times, with linearly increasing backoff. this gives time for the bulk queue to be processed
        # if necessary (in which case we'll get BulkIndexError with error 429, too many requests).
        for i in range(10):
            try:
                CaseDocument().update(cases)
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
        to_update = []
        to_create = []

        # query includes related/prefetch for elasticsearch indexing
        query = (volume.case_metadatas
            .select_related('body_cache', 'volume', 'reporter', 'court', 'jurisdiction')
            .prefetch_related('extractedcitations', 'citations'))

        # full rendering of HTML/XML
        if rerender:
            pages = list(volume.page_structures.all())
            blocks_by_id = PageStructure.blocks_by_id(pages)
            fonts_by_id = CaseFont.fonts_by_id(blocks_by_id)
            labels_by_block_id = PageStructure.labels_by_block_id(pages)
            update_fields = ['html', 'xml', 'text', 'json']

            query = (query
                .select_related('structure')
                .defer('body_cache__html', 'body_cache__xml', 'body_cache__text', 'body_cache__json'))

            for case_metadata in query:
                case_metadata.sync_case_body_cache(blocks_by_id, fonts_by_id, labels_by_block_id, rerender=rerender, save=False)

        # just rendering text/json
        else:
            query = query.defer('body_cache__xml', 'body_cache__text', 'body_cache__json').exclude(body_cache=None)
            blocks_by_id = fonts_by_id = labels_by_block_id = None
            update_fields = ['text', 'json']

        # do processing
        for case_metadata in query:
            case_metadata.sync_case_body_cache(blocks_by_id, fonts_by_id, labels_by_block_id, rerender=rerender, save=False)
            body_cache = case_metadata.body_cache
            if body_cache.id:
                to_update.append(body_cache)
            else:
                to_create.append(body_cache)

        # save
        if to_create:
            CaseBodyCache.objects.bulk_create(to_create)
        if to_update:
            CaseBodyCache.objects.bulk_update(to_update, update_fields)


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
def extract_citations_per_vol(self, volume_id):
    with record_task_status_for_volume(self, volume_id):
        extra_reporters = {'wl'}
        valid_reporters = {normalize_cite(c) for c in list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys())} | extra_reporters
        invalid_reporters = set(ascii_lowercase) | {'at', 'or', 'p.', 'c.', 'B'}
        translations = {'la.': 'Ia.', 'Yt.': 'Vt.', 'Pae.': 'Pac.'}
        cases = (CaseMetadata.objects.filter(volume_id=volume_id, in_scope=True)
                 .select_related('body_cache')
                 .only('body_cache__text'))
        # remove all extracted citations in volume before recreating
        ExtractedCitation.objects.filter(cited_by__volume_id=volume_id).delete()

        # successfully extracted citations
        extracted_citations = []
        # extracted possible citations with errors
        citation_misses_per_case = {}
        for case in cases:
            misses = []
            case_citations = []
            for match in set(re.findall(cite_extracting_regex, case.body_cache.text)):
                vol_num, reporter_str, page_num = match

                # fix known OCR errors
                if reporter_str in translations:
                    reporter_str = translations[reporter_str]

                # skip strings like 'or' that are known non-citations
                if reporter_str in invalid_reporters:
                    misses.append(reporter_str)
                    continue

                # Look for found reporter string in the official and nominative REPORTER dicts
                if normalize_cite(reporter_str) not in valid_reporters:
                    # reporter not found, removing cite and adding to misses list
                    misses.append(reporter_str)
                    continue

                cite = " ".join(match)
                case_citations.append(ExtractedCitation(
                    cite=cite,
                    normalized_cite=normalize_cite(cite),
                    cited_by=case,
                    reporter_name_original=reporter_str,
                    volume_number_original=vol_num,
                    page_number_original=page_num))

            # update cites_to field in ElasticSearch
            if settings.MAINTAIN_ELASTICSEARCH_INDEX:
                try:
                    CaseDocument._get_connection().update(
                        index=CaseDocument()._get_index(),
                        doc_type=CaseDocument._doc_type.name,
                        body={
                            'doc': {
                                'extractedcitations': [CaseDocument._fields['extractedcitations']._get_inner_field_data(e) for e in case_citations]
                            }
                        },
                        id=case.pk)
                except NotFoundError:
                    pass

            extracted_citations.extend(case_citations)
            citation_misses_per_case[case.id] = dict(Counter(misses))

        ExtractedCitation.objects.bulk_create(extracted_citations)

        Path(settings.MISSED_CITATIONS_DIR).mkdir(exist_ok=True)
        with open("%s/missed_citations-%s.csv" % (settings.MISSED_CITATIONS_DIR, self.request.id), "w+") as f:
            writer = csv.writer(f)
            for case in citation_misses_per_case:
                writer.writerow([case, len(citation_misses_per_case[case]), json.dumps(citation_misses_per_case[case])])


@shared_task(bind=True, acks_late=True)
def extract_citation_connections_per_vol(self, volume_id):
    with record_task_status_for_volume(self, volume_id):
        vol_citation_results = []
        query = """SELECT 
            cite_from.id, cite_from.name_abbreviation, cite_from.decision_date, cite_from.reporter_id, 
            cite_to.id, cite_to.name_abbreviation, cite_to.decision_date, cite_to.reporter_id 
            from capdb_casemetadata cite_from 
            inner join capdb_extractedcitation ec on cite_from.id = ec.cited_by_id 
            inner join capdb_citation c on c.normalized_cite = ec.normalized_cite 
            inner join capdb_casemetadata cite_to on c.case_id = cite_to.id
            where cite_from.volume_id = '%s';
            """ % volume_id

        with connections['capdb'].cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                vol_citation_results.append({
                    'cite_from': {
                        'id': row[0],
                        'name_abbreviation': row[1],
                        'decision_date': str(row[2]),
                        'reporter': row[3]
                    },
                    'cite_to': {
                        'id': row[4],
                        'name_abbreviation': row[5],
                        'decision_date': str(row[6]),
                        'reporter': row[7]
                    }
                })
        Path(settings.CITATIONS_DIR).mkdir(exist_ok=True)
        if len(vol_citation_results):
            with open("%s/citations-%s.json" % (settings.CITATIONS_DIR, volume_id), "w+") as f:
                json.dump(vol_citation_results, f)
