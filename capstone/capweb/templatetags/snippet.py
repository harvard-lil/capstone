import json

from django.utils.safestring import mark_safe
from django import template
from django.db import connections
from django.core.cache import cache

from capdb.models import Reporter, Jurisdiction, Court

register = template.Library()

@register.simple_tag()
def snippet(label, default=""):
    """
        Return contents of named Snippet, from cache if possible. If Snippet is not found, return default.
    """
    snippet_router = {
        'map_numbers': map_numbers,
        'search_jurisdiction_list': search_jurisdiction_list,
        'search_court_list': search_court_list,
        'search_reporter_list': search_reporter_list,
        'court_abbrev_list': court_abbrev_list,
    }
    return mark_safe(snippet_router[label]() if label in snippet_router else default)


def map_numbers():
    """ Write map_numbers snippet. """
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
    return json.dumps(output)


# label search_jurisdiction_list
def search_jurisdiction_list():
    jurisdictions = [ (jurisdiction.slug, jurisdiction.name_long)
            for jurisdiction in Jurisdiction.objects.order_by('slug').all()
            if jurisdiction.slug != 'regional']
    return json.dumps(jurisdictions)

# label search_court_list
def search_court_list():
    courts = [ (court.slug, "{}: {}".format(court.jurisdiction, court.name))
               for court in Court.objects.order_by('slug').all()]
    return json.dumps(courts)

#label search_reporter_list
def search_reporter_list():
    reporters = [ (reporter.id, "{}- {}".format(reporter.short_name, reporter.full_name))
               for reporter in Reporter.objects.order_by('full_name').all()]
    return json.dumps(reporters)

#label court_abbrev_list
def court_abbrev_list():
    return json.dumps([(court.slug, court.name) for court in Court.objects.order_by('slug').all()])
