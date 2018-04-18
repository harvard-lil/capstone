from collections import defaultdict
import pytest
from scripts import ingest_tt_data
from capdb.models import Reporter, Jurisdiction
from django.db import connection

@pytest.mark.django_db
def test_relink_reporter_jurisdiction(ingest_case_xml):

    def make_reporter_jur_map():
        output_map = defaultdict(list)
        for reporter in Reporter.objects.all():
            output_map[reporter.id].append(Jurisdiction.name)
        return output_map

    initial_map = make_reporter_jur_map()
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == 3
        cursor.execute("delete from capdb_reporter_jurisdictions")
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == 0
        ingest_tt_data.relink_reporter_jurisdiction()
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == 3
    final_map = make_reporter_jur_map()

    for reporter_id in initial_map:
        assert set(initial_map[reporter_id]) == set(final_map[reporter_id])



