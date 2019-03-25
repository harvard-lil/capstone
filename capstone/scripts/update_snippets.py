import io
import csv

from django.db import connections
from django.db.models import Count, Case, When, IntegerField
from capdb.models import Reporter, Jurisdiction, CaseMetadata, Snippet, Court
import json
from capweb.templatetags.api_url import api_url
from tqdm import tqdm

def update_all():
    update_map_numbers()
    cases_by_jurisdiction_tsv()
    cases_by_reporter_tsv()
    cases_by_decision_date_tsv()
    search_reporter_list()
    search_court_list()
    search_jurisdiction_list()

def cases_by_decision_date_tsv():
    """
        count of all cases, grouped by decision date
    """
    by_date = CaseMetadata.objects.all().values('decision_date').annotate(Count('decision_date')).order_by('decision_date')
    label="cases_by_decision_date"
    snippet_format="text/tab-separated-values"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for group in tqdm(by_date):
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
    for jurisdiction in tqdm(Jurisdiction.objects.annotate(case_count=Count('case_metadatas'))):
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
    for reporter in tqdm(Reporter.objects.annotate(case_count=Count(
            Case(When(case_metadatas__duplicative=False, then=1), output_field=IntegerField())))):
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

def update_map_numbers():
    """ Write map_numbers snippet. """
    label = "map_numbers"
    snippet_format = "application/json"
    jurisdiction_translate = {
        "regional":"Regional", "dakota-territory":"Dakota-Territory", "tribal":"Native American",
        "navajo-nation":"Navajo-Nation", "guam":"GU", "us":"US", "n-mar-i":"MP", "pr":"PR", "am-samoa":"AS",
        "vi":"VI", "nev":"US-NV", "dc":"US-DC", "nc":"US-NC", "nh":"US-NH", "pa":"US-PA", "mont":"US-MT",
        "ind":"US-IN", "la":"US-LA", "wis":"US-WI", "nj":"US-NJ", "ga":"US-GA", "sd":"US-SD", "mass":"US-MA",
        "miss":"US-MS", "cal":"US-CA", "okla":"US-OK", "nd":"US-ND", "vt":"US-VT", "ariz":"US-AZ", "w-va":"US-WV",
        "mich":"US-MI", "utah":"US-UT", "idaho":"US-ID", "wyo":"US-WY", "colo":"US-CO", "ny":"US-NY",
        "ky":"US-KY", "kan":"US-KS", "alaska":"US-AK", "fla":"US-FL", "or":"US-OR", "tenn":"US-TN", "md":"US-MD",
        "ill":"US-IL", "ohio":"US-OH", "ala":"US-AL", "sc":"US-SC", "ark":"US-AR", "ri":"US-RI", "minn":"US-MN",
        "neb":"US-NE", "conn":"US-CT", "me":"US-ME", "iowa":"US-IA", "tex":"US-TX", "del":"US-DE", "mo":"US-MO",
        "haw":"US-HI", "nm":"US-NM", "wash":"US-WA", "va":"US-VA"
    }
    cursor = connections['capdb'].cursor()
    cursor.execute(r"""
        SELECT 
          j.slug,
          COUNT(c.id) AS case_count,
          COUNT(DISTINCT c.volume_id) AS volume_count,
          COUNT(DISTINCT c.reporter_id) AS reporter_count,
          SUM(CASE WHEN (c.first_page||c.last_page)~E'^\\d+$' THEN c.last_page::integer-c.first_page::integer+1 ELSE 1 END) AS page_count
        FROM capdb_jurisdiction j 
          LEFT JOIN capdb_casemetadata c ON j.id=c.jurisdiction_id 
        WHERE
          c.duplicative IS FALSE
        GROUP BY j.id;
    """)
    # get column names from sql query
    cols = [col[0] for col in cursor.description]
    # create output where each key is a jurisdiction and each value is a dict of values from the sql query
    output = {jurisdiction_translate[row[0]]: dict(zip(cols[1:], row[1:])) for row in cursor.fetchall()}
    write_update(label, snippet_format, json.dumps(output))

def search_jurisdiction_list():
    jurisdictions = [ (jurisdiction.slug, jurisdiction.name_long)
            for jurisdiction in Jurisdiction.objects.order_by('slug').all()
            if jurisdiction.slug != 'regional' and jurisdiction.slug != 'tribal']
    write_update(
        "search_jurisdiction_list",
        "application/json",
        json.dumps(jurisdictions)
    )

def search_court_list():
    courts = [ (court.slug, "{}: {}".format(court.jurisdiction, court.name))
               for court in Court.objects.order_by('slug').all()]
    write_update(
        "search_court_list",
        "application/json",
        json.dumps(courts)
    )

def search_reporter_list():
    reporters = [ (reporter.id, "{}- {}".format(reporter.short_name, reporter.full_name))
               for reporter in Reporter.objects.order_by('short_name').all()]
    write_update(
        "search_reporter_list",
        "application/json",
        json.dumps(reporters)
    )

def write_update(label, snippet_format, contents):
    try:
        snippet = Snippet.objects.get(label=label)
    except Snippet.DoesNotExist:
        snippet = Snippet()
        snippet.label=label
        snippet.format=snippet_format
    snippet.contents = contents
    snippet.save()


