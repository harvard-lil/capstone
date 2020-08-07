from pathlib import Path
from simple_history.manager import HistoryManager

import django.apps
from django.conf import settings
from django.db import connections

from capdb.models import Citation, CaseMetadata, CaseBodyCache, Reporter, Court, VolumeMetadata, Jurisdiction, \
    ExtractedCitation, CaseAnalysis
from .helpers import nsmap


def run_sql_file(cursor, file_name):
    """ Run a sql file in the postgres/ folder """
    cursor.execute(Path(settings.BASE_DIR, "../services/postgres", file_name).read_text())

def extension_installed(cursor, ext_name):
    cursor.execute("select * from pg_extension where extname='%s';" % ext_name)
    return len(cursor.fetchall()) > 0

def extension_available(cursor, ext_name):
    cursor.execute("select * from pg_available_extensions where name='%s';" % ext_name)
    return len(cursor.fetchall()) > 0

def create_extension(cursor, ext_name):
    cursor.execute("CREATE EXTENSION %s;" % ext_name)

def update_postgres_env(db='capdb'):
    """
        Write or replace stored functions and triggers in postgres. This makes sure that the postgres environment matches
        our models. Queries here should be idempotent, so they're safe to run whenever migrations are run, or any
        other time.
    """
    with connections[db].cursor() as cursor:
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

        ### CaseLastUpdate triggers ###

        run_sql_file(cursor, "last_update_function.sql")
        # List all fields that go into generating the case documents in capapi.documents.
        # For Elasticsearch to notice that a case has changed, the field has to be listed here.
        last_update_models = [
            {
                'model': CaseMetadata,
                'case_field': 'id',
                'fields': [
                    'name',
                    'name_abbreviation',
                    'decision_date_original',
                    'decision_date',
                    'docket_number',
                    'first_page',
                    'last_page',
                    'frontend_url',
                    'jurisdiction_id',
                    'court_id',
                    'reporter_id',
                    'volume_id',
                    'in_scope',
                ],
            },
            {
                'model': Citation,
                'case_field': 'case_id',
                'fields': ['type', 'cite'],
            },
            {
                'model': CaseBodyCache,
                'case_field': 'metadata_id',
                'fields': ['json', 'html'],
            },
            {
                'model': ExtractedCitation,
                'case_field': 'cited_by_id',
                'fields': ['cite'],
            },
            {
                'model': CaseAnalysis,
                'case_field': 'case_id',
                'fields': ['value'],
            },
        ]
        fkey_update_models = [
            {
                'model': Reporter,
                'case_field': 'reporter_id',
                'fields': ['full_name'],
            },
            {
                'model': Court,
                'case_field': 'court_id',
                'fields': ['name', 'name_abbreviation', 'slug'],
            },
            {
                'model': VolumeMetadata,
                'case_field': 'volume_id',
                'fields': ['volume_number'],
            },
            {
                'model': Jurisdiction,
                'case_field': 'jurisdiction_id',
                'fields': ['whitelisted', 'name', 'name_long', 'slug'],
            },
        ]
        def get_change_query(fields):
            return " or ".join('$1.%s != $2.%s' % (f, f) for f in fields)
        for model in last_update_models:
            cursor.execute("""
                    DROP TRIGGER IF EXISTS last_update_trigger ON {table};
                    CREATE TRIGGER last_update_trigger
                    AFTER INSERT OR DELETE OR UPDATE OF {fields}
                        ON {table}
                        FOR EACH ROW
                    EXECUTE PROCEDURE track_last_update(%s, %s);
                """.format(table=model['model']._meta.db_table, fields=", ".join(model['fields'])),
                (model['case_field'], get_change_query(model['fields'])),
            )
        for model in fkey_update_models:
            cursor.execute("""
                    DROP TRIGGER IF EXISTS fkey_last_update_trigger ON {table};
                    CREATE TRIGGER fkey_last_update_trigger
                    AFTER UPDATE OF {fields}
                        ON {table}
                        FOR EACH ROW
                    EXECUTE PROCEDURE fkey_last_update(%s, %s, %s);
                """.format(table=model['model']._meta.db_table, fields=", ".join(model['fields'])),
                (model['case_field'], model['model']._meta.pk.name, get_change_query(model['fields'])),
            )

        ### Versioning ###

        # make sure the versioning() function exists in postgres
        # note: versioning can be done with a C extension that we check for, or with a fallback PL/pgSQL function.
        # if both of these turn out not to work, we could also try a plv8 version -- see
        # https://github.com/harvard-lil/capstone/blob/219b5e45d004b607e16b7eb0711b0b30f7ed464f/capstone/scripts/set_up_postgres.py#L27
        if not extension_installed(cursor, 'temporal_tables'):
            if extension_available(cursor, 'temporal_tables'):
                create_extension(cursor, 'temporal_tables')
            else:
                # if the temporal tables extension is not available, install a pure postgres version
                print("WARNING: temporal_tables extension is not installed. Versioning will be slower. See https://pgxn.org/dist/temporal_tables/")
                run_sql_file(cursor, "versioning_function.sql")

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
            # we don't currently use these views, and their existence prevents running migrations that modify columns
            # on tables with history, so let's disable for now:
            # fields = sorted(field.get_attname() for field in model._meta.get_fields() if field.concrete and not field.many_to_many)
            # cursor.execute("DROP VIEW IF EXISTS {table}_with_history;".format(table=model._meta.db_table))
            # cursor.execute("""
            #     CREATE VIEW {table}_with_history AS
            #         SELECT {fields} FROM {table}
            #     UNION ALL
            #         SELECT {fields} FROM {table}_history;
            # """.format(
            #     table=model._meta.db_table,
            #     fields=", ".join(fields),
            # ))
