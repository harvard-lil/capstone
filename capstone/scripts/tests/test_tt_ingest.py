import pytest
from scripts import ingest_tt_data

from django.db import connection

@pytest.mark.django_db
def test_relink_reporter_jurisdiction(ingest_case_xml):
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == 3
        cursor.execute("delete from capdb_reporter_jurisdictions")
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == 0
        ingest_tt_data.relink_reporter_jurisdiction()
        cursor.execute("select count(*) from capdb_reporter_jurisdictions")
        assert cursor.fetchone()[0] == 3



