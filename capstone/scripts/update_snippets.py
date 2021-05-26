import io
import csv
from collections import defaultdict

from django.db import connections
from django.db.models import Count, Q
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
    court_abbrev_list()
    search_jurisdiction_list()

def cases_by_decision_date_tsv():
    """
        count of all cases, grouped by decision date
    """
    by_date = (CaseMetadata.objects
        .in_scope()
        .values('decision_date_original')
        .annotate(Count('decision_date_original'))
        .order_by('decision_date_original'))
    label="cases_by_decision_date"
    snippet_format="text/tab-separated-values"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t', quoting=csv.QUOTE_NONNUMERIC)

    # count dates
    date_counter = defaultdict(int)
    for group in tqdm(by_date):
        print(group)
        date = group['decision_date_original']
        count = group['decision_date_original__count']
        # count year
        date_counter[date[:4]] += count
        # count year-month
        if len(date) > 4:
            date_counter[date[:7]] += count
        # count year-month-day
        if len(date) > 7:
            date_counter[date] += count

    # write dates
    cases_url = api_url('cases-list')
    for date, count in date_counter.items():
        max_date = date + "0000-12-31"[len(date):]
        writer.writerow([
            date,
            count,
            f"{cases_url}?decision_date__gte={date}&decision_date__lte={max_date}",
        ])

    write_update(label, snippet_format, output.getvalue())

def cases_by_jurisdiction_tsv():
    """
        iterate through all reporters, tally each case, output TSV
    """
    label="cases_by_jurisdiction"
    snippet_format="text/tab-separated-values"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for jurisdiction in tqdm(Jurisdiction.objects.order_by('name').annotate(case_count=Count('case_metadatas', filter=Q(case_metadatas__in_scope=True)))):
        if jurisdiction.case_count == 0:
            continue
        writer.writerow(
            [
                jurisdiction.name,
                jurisdiction.name_long,
                jurisdiction.case_count,
                "{}?jurisdiction={}".format(api_url('cases-list'), jurisdiction.slug),
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
    for reporter in tqdm(Reporter.objects.order_by('full_name').annotate(case_count=Count('case_metadatas', filter=Q(case_metadatas__in_scope=True)))):
        if reporter.case_count == 0:
            continue
        writer.writerow(
            [
                reporter.short_name,
                reporter.full_name,
                reporter.case_count,
                "{}?reporter={}".format(api_url('cases-list'), reporter.pk),
                "{}{}".format(api_url('reporter-list'), reporter.pk)
            ]
        )

    write_update(label, snippet_format, output.getvalue())

def update_map_numbers():
    """ Write map_numbers snippet. """
    label = "map_numbers"
    snippet_format = "application/json"
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
          c.in_scope IS True
        GROUP BY j.id;
    """)
    # get column names from sql query
    cols = [col[0] for col in cursor.description]
    # create output where each key is a jurisdiction and each value is a dict of values from the sql query
    output = {row[0]: dict(zip(cols[1:], row[1:])) for row in cursor.fetchall()}
    write_update(label, snippet_format, json.dumps(output))

def search_jurisdiction_list():
    jurisdictions = [ (jurisdiction.slug, jurisdiction.name_long)
            for jurisdiction in Jurisdiction.objects.order_by('slug').all()
            if jurisdiction.slug != 'regional']
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
               for reporter in Reporter.objects.order_by('full_name').all()]
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


def court_abbrev_list():
    courts = []
    for court in Court.objects.order_by('slug').all():
        if court.jurisdiction and court.jurisdiction.name:
            courts.append("({}) {}".format(court.jurisdiction.name, court.name))
        else:
            courts.append(court.name)

    write_update(
        "court_abbrev_list",
        "application/json",
        json.dumps(courts)
    )
