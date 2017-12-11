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