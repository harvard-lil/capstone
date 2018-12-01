from collections import defaultdict
import pytest
from django.db import connections

from scripts import ingest_tt_data
from capdb.models import Reporter, Jurisdiction

@pytest.mark.django_db
def test_relink_reporter_jurisdiction(ingest_case_xml):

    def make_reporter_jur_map():
        output_map = defaultdict(list)
        for reporter in Reporter.objects.all():
            output_map[reporter.id].append(Jurisdiction.name)
        return output_map

    initial_map = make_reporter_jur_map()
    with connections['capdb'].cursor() as cursor:
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        number_of_existing_reporter_jurisdictions = cursor.fetchone()[0]
        assert  number_of_existing_reporter_jurisdictions > 0
        cursor.execute("delete from capdb_reporter_jurisdictions")
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == 0
        ingest_tt_data.relink_reporter_jurisdiction()
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == number_of_existing_reporter_jurisdictions
    final_map = make_reporter_jur_map()

    for reporter_id in initial_map:
        assert set(initial_map[reporter_id]) == set(final_map[reporter_id])



