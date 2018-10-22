import json
from collections import defaultdict
from pathlib import Path

from django.contrib.admin.utils import flatten
from simple_history.manager import HistoryManager

import django.apps
from django.conf import settings
from django.db import connections

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


        ### Full text search ###
        set_case_search_trigger()
        # install rum for full text indexing
        if not extension_installed(cursor, 'rum'):
            if extension_available(cursor, 'rum'):
                create_extension(cursor, 'rum')
            else:
                print("WARNING: rum extension not available; full text search queries will fail")

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
            fields = sorted(field.get_attname() for field in model._meta.get_fields() if field.concrete and not field.many_to_many)
            cursor.execute("""
                DROP VIEW IF EXISTS {table}_with_history;
                CREATE VIEW {table}_with_history AS
                    SELECT {fields} FROM {table}
                UNION ALL
                    SELECT {fields} FROM {table}_history;
            """.format(
                table=model._meta.db_table,
                fields=", ".join(fields),
            ))


        ### Denormalization triggers ###

        # install triggers to be run on tables that are the source or destination of denormalized fields
        cursor.execute("CREATE EXTENSION IF NOT EXISTS plv8;")
        run_sql_file(cursor, "denormalize_dest.js")
        run_sql_file(cursor, "denormalize_source.js")

        # get all triggers to be created
        dest_triggers, source_triggers = get_denormalization_triggers()

        # create destination triggers -- these are tables with denormalized fields that should be updated
        # if the foreign key to a source table changes
        for dest_table, param_lists in dest_triggers.items():
            # convert [(a,b,c,d),(e,f,g,h)] to [a,b,c,json.dumps(d),e,f,g,json.dumps(h)]
            params = flatten(param_list[:3] + (json.dumps(param_list[3]),) for param_list in param_lists)
            cursor.execute("""
                DROP TRIGGER IF EXISTS denormalize_dest ON {table};
                CREATE TRIGGER denormalize_dest
                    BEFORE INSERT OR UPDATE
                    ON {table} FOR EACH ROW
                    EXECUTE PROCEDURE denormalize_dest({placeholders});
                
            """.format(
                table=dest_table,
                placeholders=", ".join(["%s"]*len(params))
            ), params)

        # create source triggers -- these are tables with information that should be copied to other tables
        # if changed
        for source_table, param_lists in source_triggers.items():
            params = flatten(param_list[:3] + (json.dumps(param_list[3]),) for param_list in param_lists)
            cursor.execute("""
                DROP TRIGGER IF EXISTS denormalize_source ON {table};
                CREATE TRIGGER denormalize_source
                    BEFORE UPDATE
                    ON {table} FOR EACH ROW
                    EXECUTE PROCEDURE denormalize_source({placeholders});

            """.format(
                table=source_table,
                placeholders=", ".join(["%s"] * len(params))
            ), params)

def get_denormalization_triggers():
    """
        Loop through application models and get parameters for all triggers that should be run, based
        on models' denormalized_fields attribute.

        Return value will look like this:
            dest_triggers = {
                'capdb_casemetadata': [
                    ('capdb_jurisdiction', 'jurisdiction_id', 'id', {'name': 'jurisdiction_name'}),
                    ('capdb_court', 'court_id', 'id', {'name': 'court_name'}),
                ]
            },
            source_triggers = {
                'capdb_jurisdiction': [
                    ('capdb_casemetadata', 'jurisdiction_id', 'id', {'name': 'jurisdiction_name'}),
                ],
                'capdb_court': [
                    ('capdb_casemetadata', 'court_id', 'id', {'name': 'court_name'}),
                ]
            }
    """
    dest_triggers = defaultdict(lambda: defaultdict(dict))
    source_triggers = defaultdict(lambda: defaultdict(dict))

    for model in django.apps.apps.get_models():
        if not hasattr(model, 'denormalized_fields'):
            continue

        # loop through pairs like ('jurisdiction_name', 'jurisdiction__name'), meaning the jurisdiction_name field
        # on this model should be copied from jurisdiction__name ...
        for dest_field_name, source_field in model.denormalized_fields.items():

            # from that pair, extract the necessary database info -- source_table, dest_table, and joining_columns
            foreign_key_name, source_field_name = source_field.split('__')
            foreign_key_field = model._meta.get_field(foreign_key_name)
            joining_columns = foreign_key_field.get_joining_columns()[0]
            dest_table = model._meta.db_table
            source_table = foreign_key_field.related_model._meta.db_table

            # record that the destination field should be included in triggers for the source table and destination table
            dest_triggers[dest_table][(source_table,) + joining_columns][source_field_name] = dest_field_name
            source_triggers[source_table][(dest_table,) + joining_columns][source_field_name] = dest_field_name

    # return flattened versions of the dest and source dictionaries
    return (
        {table: [k+(v,) for k, v in relations.items()] for table, relations in dest_triggers.items()},
        {table: [k+(v,) for k, v in relations.items()] for table, relations in source_triggers.items()},
    )


def initialize_denormalization_fields(*args, **kwargs):
    """
        Run UPDATE query for all tables with denormalized fields, to initialize the values of existing rows.
        This should be run to populate any new denormalized_fields that are added, and can be rerun harmlessly if desired.
        This function takes *args, **kwargs so it can be called from RunPython in a migration.
    """
    with connections['capdb'].cursor() as cursor:

        # for each destination table, construct a sql query that updates the table based on all source tables
        dest_triggers, _ = get_denormalization_triggers()
        for dest_table, sources in dest_triggers.items():

            values = []
            left_joins = []

            # for each source table, collect the necessary parts of the sql query
            for source_table, dest_join_field, source_join_field, field_map in sources:

                # collect assignments like "jurisdiction_name=capdb_jurisdiction.name"
                for source_field, dest_field in field_map.items():
                    values.append("%s=%s.%s" % (dest_field, source_table, source_field))

                # collect joins like "LEFT JOIN capdb_jurisdiction ON dest.jurisdiction_id=capdb_jurisdiction.id"
                left_joins.append("LEFT JOIN {source_table} ON dest.{dest_join_field}={source_table}.{source_join_field}".format(
                    source_table=source_table,
                    dest_join_field=dest_join_field,
                    source_join_field=source_join_field,
                ))

            # build and run query
            cursor.execute("""
                UPDATE {dest_table}
                SET {values}
                FROM {dest_table} AS dest
                {left_joins}
                WHERE dest.id={dest_table}.id
            """.format(
                dest_table=dest_table,
                values=", ".join(values),
                left_joins=" ".join(left_joins),
            ))


def set_case_search_trigger():
    with connections['capdb'].cursor() as cursor:
        cursor.execute("""
            DROP TRIGGER IF EXISTS case_search_update_trigger ON capdb_casetext;
            CREATE TRIGGER case_search_update_trigger
            BEFORE INSERT OR UPDATE ON capdb_casetext
            FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger('tsv', 'pg_catalog.english', 'text');
        """)