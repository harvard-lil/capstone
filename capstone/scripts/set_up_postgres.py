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

        # ### VERSIONING STUFF ###
        #
        # # function called when a versioned record is updated or deleted:
        # con.execute("""
        #     CREATE OR REPLACE FUNCTION versioning() RETURNS trigger AS $$
        #         var ql = plv8.quote_literal;
        #         var qi = plv8.quote_ident;
        #         var historyTableName = TG_TABLE_NAME+"_history";
        #
        #         // copy old record from primary table to history table, updating sys_period to indicate
        #         // that validity of this record ends now:
        #         var now = plv8.execute("SELECT text(now())")[0].text;  // use text() to stop plv8 converting to Date() object
        #         var validityStartDate = OLD.sys_period.slice(2, -3);
        #         if(validityStartDate >= now){
        #             throw "Validity start date should never be later than now. Did server time change?";
        #         }
        #         OLD.sys_period = "[" + validityStartDate + "," + now + ")";
        #         var keys = Object.keys(OLD).map(function(k){ return qi(k) }).join(', ');
        #         var values = Object.keys(OLD).map(function(k){ return ql(OLD[k]) }).join(', ');
        #         plv8.execute("INSERT INTO "+qi(historyTableName)+" ("+keys+") VALUES ("+values+")");
        #
        #         // on update, set validity of new record to start now
        #         if (TG_OP == "UPDATE") {
        #             NEW.sys_period = "[" + now + ",)";
        #             return NEW;
        #         }
        #     $$ LANGUAGE "plv8";
        # """)
        #
        # # setup for each versioned table:
        # versioned_models = versioned_objects(getattr(models, attr) for attr in dir(models))
        # for model in versioned_models:
        #     # call versioning() on update/delete:
        #     con.execute("""
        #         DROP TRIGGER IF EXISTS versioning_trigger ON {table};
        #         CREATE TRIGGER versioning_trigger
        #         BEFORE UPDATE OR DELETE ON {table}
        #         FOR EACH ROW EXECUTE PROCEDURE versioning();
        #     """.format(table=model.__tablename__))
        #
        #     # create combined table_with_history views:
        #     con.execute("""
        #         CREATE OR REPLACE VIEW {table}_with_history AS
        #             SELECT * FROM {table}
        #         UNION ALL
        #             SELECT * FROM {table}_history;
        #     """.format(table=model.__tablename__))
        #
        #     # TODO: update privileges so table_with_history views are read-only and table_history tables can only be updated by trigger
