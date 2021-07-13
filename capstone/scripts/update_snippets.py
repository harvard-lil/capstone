from django.db import connections
from capdb.models import Reporter, Jurisdiction, Snippet, Court
import json

def update_all():
    update_map_numbers()
    search_reporter_list()
    search_court_list()
    court_abbrev_list()
    search_jurisdiction_list()

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
    courts = [(court.slug, court.name) for court in Court.objects.order_by('slug').all()]

    write_update(
        "court_abbrev_list",
        "application/json",
        json.dumps(courts)
    )
