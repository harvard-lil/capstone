import io
import csv
from django.db.models import Count, Case, When, IntegerField
from celery import shared_task
from capdb.models import VolumeMetadata, Reporter, Jurisdiction, CaseMetadata, Snippet
import json
from capweb.templatetags.api_url import api_url

def update_all():
    update_map_numbers()
    cases_by_jurisdiction_tsv()
    cases_by_reporter_tsv()
    cases_by_decision_date_tsv()

def cases_by_decision_date_tsv():
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

def cases_by_jurisdiction_tsv():
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


def cases_by_reporter_tsv():
    """
        iterate through all jurisdictions, tally each case, output TSV
    """
    label="cases_by_reporter"
    snippet_format="text/tab-separated-values"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for reporter in Reporter.objects.annotate(case_count=Count(
            Case(When(case_metadatas__duplicative=False, then=1), output_field=IntegerField()))):
        if reporter.case_count == 0:
            continue
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
    results = map_volume_tally.chunks([ (vol, ) for vol in VolumeMetadata.objects
        .values_list('pk', flat=True)], chunk_size)\
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
                    output[map_id][count] += result[map_id][count]

    write_update(label, snippet_format, json.dumps(output))


@shared_task
def map_volume_tally(volume_barcode):
    """
        create or update counts for each volume. It's in a dict keyed by MAP IDs (jurisdiction essentially) because,
        which correspond to the map SVG on the homepage. We have to count this per-volume because some volumes might
        contain multiple jurisdictions. This method does result in one single regional volume being added to the count
        for every jurisdiction that has (non-duplicative) cases in that region. Same with pages.
    """
    jurisdiction_translate = {
        "regional":"Regional", "dakota-territory":"Dakota-Territory", "native-american":"Native American",
        "navajo-nation":"Navajo-Nation", "guam":"GU", "us":"US", "n-mar-i":"MP", "pr":"PR", "am-samoa":"AS",
        "vi":"VI", "nev":"US-NV", "dc":"US-DC", "nc":"US-NC", "nh":"US-NH", "pa":"US-PA", "mont":"US-MT",
        "ind":"US-IN", "la":"US-LA", "wis":"US-WI", "nj":"US-NJ", "ga":"US-GA", "sd":"US-SD", "mass":"US-MA",
        "miss":"US-MS", "cal":"US-CA", "okla":"US-OK", "nd":"US-ND", "vt":"US-VT", "ariz":"US-AZ", "w-va":"US-WV",
        "mich":"US-MI", "utah":"US-UT", "idaho":"US-ID", "wyo":"US-WY", "colo":"US-CO", "ny":"US-NY",
        "ky":"US-KY", "kan":"US-KS", "alaska":"US-AK", "fla":"US-FL", "or":"US-OR", "tenn":"US-TN", "md":"US-MD",
        "ill":"US-IL", "ohio":"US-OH", "ala":"US-AL", "sc":"US-SC", "ar":"US-AR", "ri":"US-RI", "minn":"US-MN",
        "neb":"US-NE", "conn":"US-CT", "me":"US-ME", "iowa":"US-IA", "tex":"US-TX", "del":"US-DE", "mo":"US-MO",
        "haw":"US-HI", "nm":"US-NM", "wash":"US-WA", "va":"US-VA"
    }
    tally = {}
    volume = VolumeMetadata.objects.get(pk=volume_barcode)
    # just loop through the cases
    for case in volume.case_metadatas.select_related("jurisdiction").all():

        if case.jurisdiction:
            map_id = jurisdiction_translate[case.jurisdiction.slug]
            if map_id not in tally:
                tally[map_id] = {}
                tally[map_id]['case_count'] = 0
                tally[map_id]['volume_count'] = 1
                tally[map_id]['page_count'] = 0
                tally[map_id]['reporter_count'] = 1
            tally[map_id]['case_count'] += 1
            tally[map_id]['page_count'] += int(case.last_page) - int(case.first_page) + 1
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