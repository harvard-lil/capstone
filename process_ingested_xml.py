def build_case_page_join_table(session, volume_id=None):
    """
        Add entries to the join table between Cases and Pages.

        If volume_id is provided, only index cases with that volume_id.
    """
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
                AND c.id NOT IN (SELECT case_id FROM cap_case_page)
                %s
            ) as subq
        WHERE subq.page_barcode=p.barcode;
    """ % ("AND v.id=:volume_id" if volume_id else "")
    session.execute(sql, params)
