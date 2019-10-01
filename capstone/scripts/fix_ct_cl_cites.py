import csv
import re
import sys

from capdb.models import Citation, EditLog, Reporter, CaseMetadata

"""
    Usage: fab run_script:scripts.fix_ct_cl_cites

    This script deletes or updates incorrectly-detected citations from the Court of Claims Reports (Ct. Cl.) reporter.
    Additional citations were incorrectly detected for these volumes because case head matter often lists the citations 
    of earlier cases in the procedural history ( https://github.com/harvard-lil/capstone/issues/1192 ).
    
    Cases in this reporter come in four varieties:
    
        1) Correct:                                                    1 Ct. Cl. 1
        2) Correct, with a correctly detected parallel cite to F.2d:   206 Ct. Cl. 354, 513 F.2d 1342
        3) Incorrect cite appended to F.2d cite with semicolon:        207 Ct. Cl. 254, "518 F.2d 556; 31 Ind. Cl. Comm. 89"
        4) Incorrect additional cites:                                 19 Ct. Cl. 714, "16 Ct. Cl. 361; 111 U. S. 609"
     
    This script should ignore type 1 and type 2; edit the second cite in type 3; and delete the second cite for type 4.
"""

def main(dry_run='true'):
    # get cases with at least one cite not matching 123 Ct. Cl. 456 (non-type-1 cases):
    ct_cl_reporter = Reporter.objects.get(full_name='Court of Claims Reports')
    bad_cites = Citation.objects.filter(case__reporter=ct_cl_reporter).select_related('case').extra(
        where=[r"NOT cite ~ '^\d+ Ct\. Cl\. \d+$'"]).prefetch_related('case__citations')
    bad_cases = set(c.case for c in bad_cites)
    to_delete = []
    to_update = []
    to_reindex = []
    changed_cites = set()
    out = csv.writer(sys.stdout)
    out.writerow(['case.id', 'result', 'val1', 'val2'])

    # handle each bad case:
    for case in bad_cases:
        first, *rest = case.citations.all()

        # special case -- doesn't follow the pattern
        if case.id == 10809316:
            old_val = first.cite
            first.cite = "122 Ct. Cl. 348"
            to_update.append(first)
            to_reindex.append(case)
            out.writerow([case.id, "special case", old_val, first.cite])
            continue

        # we should always have one correct cite at the front of the list:
        if not re.match(r'\d+ Ct. Cl. \d+$', first.cite):
            out.writerow([case.id, "error", first, str(rest)])
            continue

        # handle skipping or updating F.2d cites:
        if len(rest) == 1:
            second = rest[0]

            # type 2:
            if re.match(r'\d+ F.2d \d+$', second.cite):
                out.writerow([case.id, "skip", second.cite])
                continue

            # type 3:
            if re.match(r'\d+ F.2d \d+;.*$', second.cite):
                old_val = second.cite
                second.cite = old_val.split(';', 1)[0]
                to_update.append(second)
                to_reindex.append(case)
                changed_cites.add(old_val)
                changed_cites.add(second.cite)
                out.writerow([case.id, "update", old_val, second.cite])
                continue

        # type 4:
        delete_cites = [c.cite for c in rest]
        changed_cites.update(delete_cites)
        out.writerow([case.id, "delete"]+delete_cites)
        to_delete.extend(rest)
        to_reindex.append(case)

    # apply edits:
    if dry_run == 'false':
        with EditLog(
                description='Remove incorrectly-detected citations from Ct. Cl. reporter. '
                            'See https://github.com/harvard-lil/capstone/issues/1192'
        ).record():
            Citation.objects.bulk_update(to_update, ['cite'])
            for obj in to_delete:
                obj.delete()
            CaseMetadata.update_frontend_urls(changed_cites)
            CaseMetadata.reindex_cases(to_reindex)