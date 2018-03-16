from pathlib import Path
from simple_history.manager import HistoryManager

import django.apps
from django.conf import settings
from django.db import connection

from .helpers import nsmap

def update_postgres_env():
    """
        Write or replace stored functions and triggers in postgres. This makes sure that the postgres environment matches
        our models. Queries here should be idempotent, so they're safe to run whenever migrations are run, or any
        other time.
    """
    with connection.cursor() as cursor:
        ### XML namespace stuff ###

        # wrapper for the postgres `xpath(<xpath>, <xml>, <namespaces>)` function with our namespaces preloaded.
        namespaces = ", ".join("ARRAY['%s', '%s']" % (k, v) for k, v in nsmap.items())
        cursor.execute("""
            CREATE OR REPLACE FUNCTION ns_xpath(text, xml) RETURNS xml[] AS $$
                begin
                    return xpath($1, $2, ARRAY[%s]);
                end
            $$ LANGUAGE plpgSQL;
        """ % namespaces)

        # make sure the versioning() function exists in postgres
        # note: versioning can be done with a C extension that we check for, or with a fallback PL/pgSQL function.
        # if both of these turn out not to work, we could also try a plv8 version -- see
        # https://github.com/harvard-lil/capstone/blob/219b5e45d004b607e16b7eb0711b0b30f7ed464f/capstone/scripts/set_up_postgres.py#L27
        cursor.execute("select * from pg_extension where extname='temporal_tables';")
        if len(cursor.fetchall()) == 0:
            # if the temporal tables extension is not active, install a pure postgres version
            print("WARNING: temporal_tables extension is not installed. Versioning will be slower. See https://pgxn.org/dist/temporal_tables/")
            cursor.execute((Path(settings.BASE_DIR) / "../services/postgres/versioning_function.sql").read_text())

        # set up versioning for versioned tables
        for model in django.apps.apps.get_models():
            # skip models that don't have a `history = TemporalHistoricalRecords()` attribute
            if not isinstance(getattr(model, 'history', None), HistoryManager):
                continue

            # make sure versioned model has sys_period column
            cursor.execute("""
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS sys_period tstzrange NOT NULL DEFAULT tstzrange(current_timestamp, null);
            """.format(table=model._meta.db_table))

            # create trigger
            cursor.execute("""
                DROP TRIGGER IF EXISTS versioning_trigger ON {table};
                CREATE TRIGGER versioning_trigger
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE PROCEDURE versioning('sys_period', '{table}_history', true);
            """.format(table=model._meta.db_table))

            # create combined table_with_history views:
            fields = sorted(field.get_attname() for field in model._meta.get_fields() if field.concrete and not field.many_to_many)
            cursor.execute("""
                CREATE OR REPLACE VIEW {table}_with_history AS
                    SELECT {fields} FROM {table}
                UNION ALL
                    SELECT {fields} FROM {table}_history;
            """.format(
                table=model._meta.db_table,
                fields=", ".join(fields),
            ))