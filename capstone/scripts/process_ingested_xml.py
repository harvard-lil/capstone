from django.db import connections
from capdb.models import VolumeXML, PageXML


def build_case_page_join_table(volume_id=None):
    """
        Add entries to the join table between Cases and Pages.

        If volume_id is provided, only index cases with that volume_id.
    """
    # remove existing relations
    if volume_id:
        case_page_join_model = PageXML.cases.through
        case_page_join_model.objects.filter(casexml__volume_id=volume_id).delete()

    # add new relations

    with connections['capdb'].cursor() as cursor:
        params = {'volume_id': volume_id} if volume_id else {}
        sql = """
            INSERT INTO capdb_pagexml_cases (pagexml_id, casexml_id)
            SELECT p.id, casexml_id
            FROM capdb_pagexml p,
                (SELECT c.id as casexml_id,
                    v.metadata_id || '_' || substring(
                        text(
                            unnest(
                                ns_xpath('//mets:fileGrp[@USE="alto"]/mets:file/@ID', c.orig_xml)
                            )
                        ), 6) as page_barcode
                FROM capdb_casexml c, capdb_volumexml v
                WHERE
                    v.id=c.volume_id
                    AND NOT EXISTS (SELECT 1 FROM capdb_pagexml_cases cp WHERE cp.casexml_id=c.id)
                    %s
                ) as subq
            WHERE subq.page_barcode=p.barcode;
        """ % ("AND v.id=%(volume_id)s" if volume_id else "")
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
    with connections['capdb'].cursor() as cursor:
        sql = """
            CREATE OR REPLACE FUNCTION get_opinions(xml) RETURNS json AS $$
            DECLARE
              opinion_array text[] := (xpath('//casebody:opinion/@type', $1, ARRAY[ARRAY['casebody','http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1']])::text[]);
              result text[];
              opinion_type text;
            BEGIN
              FOREACH opinion_type IN ARRAY opinion_array
              LOOP
                result := result || ARRAY[opinion_type, (array_to_json(
                  substring(
                    xpath(
                      format('//casebody:opinion[@type="%I"]/casebody:author/text()', opinion_type
                    ), $1, ARRAY[ARRAY['casebody','http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1']]
                  )::text, '\S(?:.*)\S*')::text[]
                )::text)];
              END LOOP;
              RETURN json_object(result::text[]);
            END;
            $$ LANGUAGE plpgsql;

            UPDATE capdb_casemetadata cm
            SET attorneys=array_to_json(ns_xpath('//casebody:attorneys/text()', cx.orig_xml)::text[]),
            judges=array_to_json(ns_xpath('//casebody:judges/text()', cx.orig_xml)::text[]),
            parties=array_to_json(ns_xpath('//casebody:parties/text()', cx.orig_xml)::text[]),
            opinions=get_opinions(cx.orig_xml)
            FROM capdb_casexml AS cx
            WHERE cm.id = cx.metadata_id;
        """
        cursor.execute(sql)
