import io
import csv
from django.db.models import Count
from celery import shared_task
from capdb.models import VolumeMetadata, Reporter, Jurisdiction, CaseMetadata, Snippet
import json
from capweb.templatetags.api_url import api_url

def update_all():
    update_map_numbers()
    cases_by_jurisdiction_tsv()
    cases_by_reporter_tsv()
    cases_by_decision_date()

def cases_by_decision_date():
    """
        count of all cases, grouped by decision date
    """
    by_date = CaseMetadata.objects.all().values('decision_date').annotate(Count('decision_date')).order_by('decision_date')
    label="cases_by_decision_date"
    snippet_format="text/tab-separated-values"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for group in by_date:
        if group['decision_date__count'] == 0:
            continue
        writer.writerow(
            [
                group['decision_date'],
                group['decision_date__count'],
                '{}?decision_date_min={}&decision_date_max={}'.format(
                    api_url('casemetadata-list'),
                    group['decision_date'],
                    group['decision_date']
                )
            ]
        )

    write_update(label, snippet_format, output.getvalue())

def cases_by_reporter_tsv():
    """
        iterate through all reporters, tally each case, output TSV
    """
    label="cases_by_jurisdiction"
    snippet_format="text/tab-separated-values"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for jurisdiction in Jurisdiction.objects.annotate(case_count=Count('case_metadatas')):
        if jurisdiction.case_count == 0:
            continue
        writer.writerow(
            [
                jurisdiction.name,
                jurisdiction.name_long,
                jurisdiction.case_count,
                "{}?jurisdiction={}".format(api_url('casemetadata-list'), jurisdiction.slug),
                "{}{}".format(api_url('jurisdiction-list'), jurisdiction.pk)
            ]
        )

    write_update(label, snippet_format, output.getvalue())


def cases_by_jurisdiction_tsv():
    """
        iterate through all jurisdictions, tally each case, output TSV
    """
    label="cases_by_reporter"
    snippet_format="text/tab-separated-values"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for reporter in Reporter.objects.annotate(case_count=Count('case_metadatas')):
        writer.writerow(
            [
                reporter.short_name,
                reporter.full_name,
                reporter.case_count,
                "{}?reporter={}".format(api_url('casemetadata-list'), reporter.pk),
                "{}{}".format(api_url('reporter-list'), reporter.pk)
            ]
        )

    write_update(label, snippet_format, output.getvalue())

###
#
# The next two functions are for updating the map numbers snippet.
#
###

def update_map_numbers(chunk_size=1000):
    """
        iterate through all volumes
        chunk into groups of chunk_size, 1000 by default
        process the vols in that chunk asynchronously with map_volume_tally via apply_async()
        move onto next chunk
        write results to snippets model
    """
    label="map_numbers"
    snippet_format="application/json"
    results = map_volume_tally.chunks([ (vol, ) for vol in VolumeMetadata.objects.values_list('pk', flat=True)], chunk_size)\
        .group()\
        .apply_async()


    output = {}
    for result_set in results.get():
        for result in result_set:
            for map_id in result.keys():
                if map_id not in output:
                    output[map_id] = {
                        'case_count': 0,
                        'page_count': 0,
                        'reporter_count': 0,
                        'volume_count': 0
                    }
                for count in result[map_id]:
                    if count == 'reporter_list':
                        continue
                    output[map_id][count] += result[map_id][count]

    write_update(label, snippet_format, json.dumps(output))


@shared_task
def map_volume_tally(volume_barcode):
    """
        create or update cases for each volume. It's in a dict keyed by MAP IDs (jurisdiction essentially) because
        some volumes might contain multiple jurisdictions.
    """
    jurisdictions = {
        "regional": {"label": "Regional", "map_id": "Regional"},
        "dakota-territory": {"label": "Dakota Territory", "map_id": "Dakota-Territory"},
        "native-american": { "label": "Native American", "map_id": "Native American"},
        "navajo-nation": {"label": "nameo", "map_id": "Navajo-Nation"},
        "guam": { "label": "Guam", "map_id": "GU"},
        "us": { "label": "Federal", "map_id": "US"},
        "n-mar-i": { "label": "Northern Mariana Islands", "map_id": "MP"},
        "pr": { "label": "Puerto Rico", "map_id": "PR"},
        "am-samoa": { "label": "American Samoa", "map_id": "AS"},
        "vi": { "label": "Virgin Islands", "map_id": "VI"},
        "nev": { "label": "Nevada", "map_id": "US-NV"},
        "dc": { "label": "Washington D.C.", "map_id": "US-DC"},
        "nc": { "label": "North Carolina", "map_id": "US-NC"},
        "nh": { "label": "New Hampshire", "map_id": "US-NH"},
        "pa": { "label": "Pennsylvania", "map_id": "US-PA"},
        "mont": { "label": "Montana", "map_id": "US-MT"},
        "ind": { "label": "Indiana", "map_id": "US-IN"},
        "la": { "label": "Louisiana", "map_id": "US-LA"},
        "wis": { "label": "Wisconsin", "map_id": "US-WI"},
        "nj": { "label": "New Jersey", "map_id": "US-NJ"},
        "ga": { "label": "Georgia", "map_id": "US-GA"},
        "sd": { "label": "South Dakota", "map_id": "US-SD"},
        "mass": { "label": "Massachusetts", "map_id": "US-MA"},
        "miss": { "label": "Mississippi", "map_id": "US-MS"},
        "cal": { "label": "California", "map_id": "US-CA"},
        "okla": { "label": "Oklahoma", "map_id": "US-OK"},
        "nd": { "label": "North Dakota", "map_id": "US-ND"},
        "vt": { "label": "Vermont", "map_id": "US-VT"},
        "ariz": { "label": "Arizona", "map_id": "US-AZ"},
        "w-va": { "label": "West Virginia", "map_id": "US-WV"},
        "mich": { "label": "Michigan", "map_id": "US-MI"},
        "utah": { "label": "Utah", "map_id": "US-UT"},
        "idaho": { "label": "Idaho", "map_id": "US-ID"},
        "wyo": { "label": "Wyoming", "map_id": "US-WY"},
        "colo": { "label": "Colorado", "map_id": "US-CO"},
        "ny": { "label": "New York", "map_id": "US-NY"},
        "ky": { "label": "Kentucky", "map_id": "US-KY"},
        "kan": { "label": "Kansas", "map_id": "US-KS"},
        "alaska": { "label": "Alaska", "map_id": "US-AK"},
        "fla": { "label": "Florida", "map_id": "US-FL"},
        "or": { "label": "Oregon", "map_id": "US-OR"},
        "tenn": { "label": "Tennessee", "map_id": "US-TN"},
        "md": { "label": "Maryland", "map_id": "US-MD"},
        "ill": { "label": "Illinois", "map_id": "US-IL"},
        "ohio": { "label": "Ohio", "map_id": "US-OH"},
        "ala": { "label": "Alabama", "map_id": "US-AL"},
        "sc": { "label": "South Carolina", "map_id": "US-SC"},
        "ar": { "label": "Arkansas", "map_id": "US-AR"},
        "ri": { "label": "Rhode Island", "map_id": "US-RI"},
        "minn": { "label": "Minnesota", "map_id": "US-MN"},
        "neb": { "label": "Nebraska", "map_id": "US-NE"},
        "conn": { "label": "Connecticut", "map_id": "US-CT"},
        "me": { "label": "Maine", "map_id": "US-ME"},
        "iowa": { "label": "Iowa", "map_id": "US-IA"},
        "tex": { "label": "Texas", "map_id": "US-TX"},
        "del": { "label": "Delaware", "map_id": "US-DE"},
        "mo": { "label": "Missouri", "map_id": "US-MO"},
        "haw": { "label": "Hawaii", "map_id": "US-HI"},
        "nm": { "label": "New Mexico", "map_id": "US-NM"},
        "wash": { "label": "Washington", "map_id": "US-WA"},
        "va": { "label": "Virginia", "map_id": "US-VA"}
    }
    tally = {}
    volume = VolumeMetadata.objects.get(pk=volume_barcode)
    for case in volume.case_metadatas.all():
        if case.jurisdiction:
            map_id = jurisdictions[case.jurisdiction.slug]['map_id']
            if map_id not in tally:
                tally[map_id] = {}
                tally[map_id]['case_count'] = 0
                tally[map_id]['volume_count'] = 0
                tally[map_id]['page_count'] = 0
                tally[map_id]['reporter_list'] = []
                tally[map_id]['reporter_count'] = 0

            tally[map_id]['case_count'] += volume.case_metadatas.count()
            tally[map_id]['volume_count'] += 1
            tally[map_id]['page_count'] += volume.volume_xml.page_xmls.count()
            tally[map_id]['reporter_list'].append(volume.reporter.pk)
            tally[map_id]['reporter_count'] = len(set(tally[map_id]['reporter_list']))
    return tally


def write_update(label, snippet_format, contents):
    try:
        snippet = Snippet.objects.get(label=label)
    except Snippet.DoesNotExist:
        snippet = Snippet()
        snippet.label=label
        snippet.format=snippet_format
    snippet.contents = contents
    snippet.save()