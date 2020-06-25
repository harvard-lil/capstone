import csv
from io import StringIO

from capdb.models import CaseMetadata, Citation, VolumeMetadata, Reporter, Court, Jurisdiction, EditLog

# copied from Google Sheet
csv_txt = """
Reporter	Volume	Wrong Jur	Correct Jur	Correct Court	Correct Reporter	Wrong Citation	Correct Citation
1084	17	N.C.	S.C.				
83	55	N.J.	N.Y.				
294	16	Pa.	Ohio				
294	*	Pa.	Ohio				
299	337	U.S.	N.J.				
324	21	Pa.	N.J.				
385	*	Ohio	Pa.				
389	*	Ohio	Pa.				
390	*	Ohio	Pa.				
392	*	Ohio	Pa.				
409	*	Ohio	Pa.				
476	21	Ark.	Kan.	Kansas Supreme Court			
476	271	N.D.	Kan.	Kansas Supreme Court			
476	32	U.S.	Kan.	Kansas Supreme Court			
485	123	Wash.	Wis.				
521	78	U.S.	Md.				
524	297	U.S.	Md.				
534	55	Pa.	Va.	Supreme Court of Appeals of Virginia			
549	358	S.C.	N.C.	Supreme Court of North Carolina			
684	419				1038		
753	19	U.S.	Am. Samoa				
694	*					D.C.	S.C.D.C. (N.S.)
776	7	Pa.	Ohio				
777	*	Pa.	Ohio				
794	*	Ohio	Pa.				
821	*	Ohio	Pa.				
823	*	Ohio	Pa.				
832	*	Ohio	Pa.				
934	715	D.C.	U.S.				
934	982	D.C.	U.S.				
942	*	N.C.	U.S.				
953	*	Pa.	Ohio				
""".strip()
fixes = list(csv.DictReader(StringIO(csv_txt), delimiter='\t'))


def write_log(log, val):
    log.write(str(val)+"\n")


def main(dry_run='true', log_file='/tmp/fix_reporter_jurs.log'):
    dry_run = dry_run != 'false'
    with open(log_file, 'a') as log:
        for fix in fixes:
            cases = CaseMetadata.objects.filter(reporter_id=fix['Reporter'])
            if fix['Volume'] != '*':
                cases = cases.filter(volume__volume_number=fix['Volume'])

            if fix['Correct Citation']:
                cites = Citation.objects.filter(case__in=cases, cite__contains=fix['Wrong Citation'])
                with EditLog(
                    description='Correct citations for reporter %s volume %s from %s to %s' % (fix['Reporter'], fix['Volume'], fix['Wrong Citation'], fix['Correct Citation']),
                    dry_run=dry_run,
                ).record():
                    actions = Citation.replace_reporter(cites, fix['Wrong Citation'], fix['Correct Citation'], dry_run=dry_run)
                for cite, old_cite, new_cite in actions:
                    write_log(log, {"action": 'fix_cite', "cite_id": cite.id, "old": old_cite, "new": new_cite})

            elif fix['Correct Reporter']:
                volume = VolumeMetadata.objects.filter(volume_number=fix['Volume'], reporter_id=fix['Reporter']).first()
                if volume is None:
                    print("WARNING: nothing to do for %s; skipping" % fix)
                    continue
                new_reporter = Reporter.objects.get(id=fix['Correct Reporter'])
                write_log(log, {"action": 'fix_reporter', "volume_id": volume.pk, "old_reporter_id": volume.reporter_id, "new_reporter_id": new_reporter.id})
                if not dry_run:
                    with EditLog(
                        description='Correct reporter for volume %s from %s to %s' % (volume.pk, volume.reporter_id, new_reporter.id)
                    ).record():
                        volume.set_reporter(new_reporter)

            else:
                cases = cases.filter(jurisdiction__name=fix['Wrong Jur'])
                new_jur = Jurisdiction.objects.get(name=fix['Correct Jur'])
                new_court = None
                if fix['Correct Court']:
                    new_court = Court.objects.get(name=fix['Correct Court'])
                to_update = []
                for case in cases.for_indexing():
                    case.jurisdiction = new_jur
                    message = {"action": 'fix_jur', "case_id": case.pk, "old_jur": fix['Wrong Jur'], "new_jur": fix['Correct Jur']}
                    if new_court:
                        message.update(old_court=case.court_id, new_court=new_court.id)
                        case.court = new_court
                    to_update.append(case)
                    write_log(log, message)
                if not to_update:
                    print("WARNING: nothing to do for %s; skipping" % fix)
                    continue
                if not dry_run:
                    with EditLog(
                        description='Correct jurisdictions in reporter %s volume %s from %s to %s' % (fix['Reporter'], fix['Volume'], fix['Wrong Jur'], fix['Correct Jur']),
                    ).record():
                        CaseMetadata.objects.bulk_update(to_update, ['court', 'jurisdiction'])
                        CaseMetadata.reindex_cases(to_update)
