import models
from helpers import pg_connect
from versioning import versioned_objects


def create_database():
    """
        CREATE DATABASE capstone;
        CREATE EXTENSION plv8;
    """

def update_postgres_env():
    """
        Write or replace stored functions and triggers in postgres. This makes sure that the postgres environment matches
        our models. Queries here should be idempotent, so they're safe to run whenever migrations are run, or any
        other time.
    """
    pg_engine = pg_connect()
    with pg_engine.connect() as con:

        ### XML namespace stuff ###

        # wrapper for the postgres `xpath(<xpath>, <xml>, <namespaces>)` function with our namespaces preloaded.
        con.execute("""
            CREATE OR REPLACE FUNCTION ns_xpath(text, xml) RETURNS xml[] AS $$
                begin
                    return xpath($1, $2, ARRAY[
                        ARRAY['METS', 'http://www.loc.gov/METS/'],
                        ARRAY['case', 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case:v1'],
                        ARRAY['casebody', 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1'],
                        ARRAY['volume', 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Volume:v1'],
                        ARRAY['xlink', 'http://www.w3.org/1999/xlink'],
                        ARRAY['alto', 'http://www.loc.gov/standards/alto/ns-v3#']]);
                end
            $$ LANGUAGE plpgSQL;
        """)

        ### VERSIONING STUFF ###

        # function called when a versioned record is updated or deleted:
        con.execute("""
            CREATE OR REPLACE FUNCTION versioning() RETURNS trigger AS $$
                var ql = plv8.quote_literal;
                var qi = plv8.quote_ident;
                var historyTableName = TG_TABLE_NAME+"_history";

                // copy old record from primary table to history table, updating sys_period to indicate
                // that validity of this record ends now:
                var now = plv8.execute("SELECT text(now())")[0].text;  // use text() to stop plv8 converting to Date() object
                var validityStartDate = OLD.sys_period.slice(2, -3);
                if(validityStartDate >= now){
                    throw "Validity start date should never be later than now. Did server time change?";
                }
                OLD.sys_period = "[" + validityStartDate + "," + now + ")";
                var keys = Object.keys(OLD).map(function(k){ return qi(k) }).join(', ');
                var values = Object.keys(OLD).map(function(k){ return ql(OLD[k]) }).join(', ');
                plv8.execute("INSERT INTO "+qi(historyTableName)+" ("+keys+") VALUES ("+values+")");

                // on update, set validity of new record to start now
                if (TG_OP == "UPDATE") {
                    NEW.sys_period = "[" + now + ",)";
                    return NEW;
                }
            $$ LANGUAGE "plv8";
        """)

        # setup for each versioned table:
        versioned_models = versioned_objects(getattr(models, attr) for attr in dir(models))
        for model in versioned_models:
            # call versioning() on update/delete:
            con.execute("""
                DROP TRIGGER IF EXISTS versioning_trigger ON {table};
                CREATE TRIGGER versioning_trigger
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE PROCEDURE versioning();
            """.format(table=model.__tablename__))

            # create combined table_with_history views:
            con.execute("""
                CREATE OR REPLACE VIEW {table}_with_history AS
                    SELECT * FROM {table}
                UNION ALL
                    SELECT * FROM {table}_history;
            """.format(table=model.__tablename__))

            # TODO: update privileges so table_with_history views are read-only and table_history tables can only be updated by trigger


def disable_constraints():
    """
        TODO: It would be cool to have a way to automatically disable and enable constraints during bulk imports.
        Currently there's no automatic code, so this is the SQL I run manually:
    """
    """
        ALTER TABLE "public"."cap_case" DROP CONSTRAINT "cap_case_volume_id_fkey";
        ALTER TABLE "public"."cap_case_page" DROP CONSTRAINT "cap_case_pages_case_id_fkey";
        ALTER TABLE "public"."cap_case_page" DROP CONSTRAINT "cap_case_pages_page_id_fkey";
        ALTER TABLE "public"."cap_page" DROP CONSTRAINT "cap_page_volume_id_fkey";
        DROP INDEX "public"."ix_cap_case_barcode" RESTRICT;
        DROP INDEX "public"."ix_cap_case_volume_id" RESTRICT;
        DROP INDEX "public"."ix_cap_page_barcode" RESTRICT;
        DROP INDEX "public"."ix_cap_page_volume_id" RESTRICT;
        DROP INDEX "public"."ix_cap_volume_barcode" RESTRICT;
    """

def enable_constraints():
    """
        TODO: It would be cool to have a way to automatically disable and enable constraints during bulk imports.
        Currently there's no automatic code, so this is the SQL I run manually:
    """
    """
        ALTER TABLE "public"."cap_page" ADD CONSTRAINT "cap_page_volume_id_fkey" FOREIGN KEY (volume_id) REFERENCES cap_volume(id);
        ALTER TABLE "public"."cap_case_page" ADD CONSTRAINT "cap_case_pages_page_id_fkey" FOREIGN KEY (page_id) REFERENCES cap_page(id);
        ALTER TABLE "public"."cap_case_page" ADD CONSTRAINT "cap_case_pages_case_id_fkey" FOREIGN KEY (case_id) REFERENCES cap_case(id);
        ALTER TABLE "public"."cap_case" ADD CONSTRAINT "cap_case_volume_id_fkey" FOREIGN KEY (volume_id) REFERENCES cap_volume(id);
        CREATE UNIQUE INDEX ix_cap_case_barcode ON cap_case USING btree (barcode);
        CREATE INDEX ix_cap_case_volume_id ON cap_case USING btree (volume_id);
        CREATE UNIQUE INDEX ix_cap_page_barcode ON cap_page USING btree (barcode);
        CREATE INDEX ix_cap_page_volume_id ON cap_page USING btree (volume_id);
        CREATE UNIQUE INDEX ix_cap_volume_barcode ON cap_volume USING btree (barcode);
    """