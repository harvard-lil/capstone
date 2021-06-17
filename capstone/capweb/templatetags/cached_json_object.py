import json

from django.utils.safestring import mark_safe
from django import template
from django.db import connections
from django.core.cache import cache
from django.conf import settings

from capdb.models import Reporter, Jurisdiction, Court

register = template.Library()

@register.simple_tag()
def cached_json_object(label, default="", force_clear=False):
    """
        Return contents of named cached_json_object, from cache if possible. If cached_json_object is not found, return default.
    """
    cached_json_object_router = {
        'map_numbers': map_numbers,
        'search_jurisdiction_list': search_jurisdiction_list,
        'search_court_list': search_court_list,
        'search_reporter_list': search_reporter_list,
        'court_abbrev_list': court_abbrev_list,
    }
    key = 'cached_json_object:{}'.format(label)
    cached_json_object = cache.get(key)

    if force_clear or (not cached_json_object and label in cached_json_object_router):
        cache.set(key, cached_json_object_router[label](), settings.CACHED_JSON_OBJECT_TIMEOUT)
        cached_json_object = cache.get(key)

    return mark_safe(cached_json_object if cached_json_object else default)


def map_numbers():
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


def search_jurisdiction_list():
    jurisdictions = [ (jurisdiction.slug, jurisdiction.name_long)
            for jurisdiction in Jurisdiction.objects.order_by('slug').all()
            if jurisdiction.slug != 'regional']
    return json.dumps(jurisdictions)

def search_court_list():
    output = []
    for court in Court.objects.order_by('slug').all():
        try:
            output.append((court.slug, "{}: {}".format(court.jurisdiction, court.name)))
        except Jurisdiction.DoesNotExist:
            output.append({court.slug: court.name})
    return json.dumps(output)

def search_reporter_list():
    reporters = [ (reporter.id, "{}- {}".format(reporter.short_name, reporter.full_name))
               for reporter in Reporter.objects.order_by('full_name').all()]
    return json.dumps(reporters)

def court_abbrev_list():
    return json.dumps([(court.slug, court.name) for court in Court.objects.order_by('slug').all()])


