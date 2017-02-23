from helpers import pg_connect

def create_postgres_functions():
    """
        Write or replace stored functions in postgres.
    """
    pg_engine = pg_connect()
    with pg_engine.connect() as con:

        # FUNCTION: ns_xpath
        # PURPOSE: wrapper for the postgres `xpath(<xpath>, <xml>, <namespaces>)` function, that has our namespaces preloaded.
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