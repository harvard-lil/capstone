from django.db import connection

from capdb.models import VolumeXML


def build_case_page_join_table(volume_id=None):
    """
        Add entries to the join table between Cases and Pages.

        If volume_id is provided, only index cases with that volume_id.
    """
    with connection.cursor() as cursor:
        params = {'volume_id': volume_id} if volume_id else {}
        sql = """
            INSERT INTO cap_case_page (page_id, case_id)
            SELECT p.id, case_id
            FROM cap_page p,
                (SELECT c.id as case_id,
                    v.barcode || '_' || substring(
                        text(
                            unnest(
                                ns_xpath('//METS:fileGrp[@USE="alto"]/METS:file/@ID', c.orig_xml)
                            )
                        ), 6) as page_barcode
                FROM cap_case c, cap_volume v
                WHERE
                    v.id=c.volume_id
                    AND NOT EXISTS (SELECT 1 FROM cap_case_page cp WHERE cp.case_id=c.id)
                    %s
                ) as subq
            WHERE subq.page_barcode=p.barcode;
        """ % ("AND v.id=:volume_id" if volume_id else "")
        cursor.execute(sql, params)


def fill_case_page_join_table():
    """ Call build_case_page_join_table for each volume ID. """
    for volume_id in VolumeXML.objects.values_list('pk', flat=True):
        print("Indexing", volume_id)
        build_case_page_join_table(volume_id)


def get_people_for_casemetadata():
    """
    judges, parties, attorneys, and opinions

    for opinions, we return array tuples, with type of opinion and opinion author
    """
    with connection.cursor() as cursor:
        sql = """
            CREATE OR REPLACE FUNCTION get_opinions(xml) RETURNS text[] AS $$
            DECLARE
              opinion_array text[] := (xpath('//casebody:opinion/@type', $1, ARRAY[ARRAY['casebody','http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1']])::text[]);
              result text[];
              opinion_type text;
            BEGIN
              FOREACH opinion_type IN ARRAY opinion_array
              LOOP
                result := result || ARRAY[opinion_type, (
                  substring(
                      xpath(
                      format('//casebody:opinion[@type="%I"]/casebody:author/text()', opinion_type
                    ), $1, ARRAY[ARRAY['casebody','http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1']]
                  )::text, '\S(?:.*\S)*')
                )];
              END LOOP;
              RETURN result;
            END;
            $$ LANGUAGE plpgsql;
        
            UPDATE capdb_casemetadata cm
            SET attorneys=ns_xpath('//casebody:attorneys/text()', cx.orig_xml),
            judges=ns_xpath('//casebody:judges/text()', cx.orig_xml),
            parties=ns_xpath('//casebody:parties/text()', cx.orig_xml),
            opinions=get_opinions(cx.orig_xml)
            FROM capdb_casexml AS cx
            WHERE cm.id = cx.metadata_id;
        """
        cursor.execute(sql)
        