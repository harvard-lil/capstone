import csv
import re
from copy import deepcopy
from pathlib import Path
from natsort import natsorted

from capdb.models import Reporter, EditLog, VolumeMetadata, Citation

"""
    This script fixes our handling of nominative reporters. We currently handle nominative reporters like this:
    
        Reporter name:  Volume numbers: Example case citation:
        Mass. (Foo)     1-4             1 Mass. (Foo) 123
        Mass. (Bar)     5-8             5 Mass. (Bar) 123
        Mass.           9-200           9 Mass. 123
        
    Volume numbering is inconsistent -- volume_number might indicate a given volume's nominative number or official number.
    
    This script associates all volumes with the official reporter, and separately associates renumbered volumes with their
    nominative reporter. The upshot is this:
    
        Reporter name:  Volume numbers: Example case citation:
        Mass.           1-200           1 Mass. 123
        Foo             1-4             1 Foo 123
        Bar             5-8             1 Bar 123
    
    Cases appearing in a nominative volume end up with two separate citations, like 1 Mass. 123, 1 Foo 123.
    
    How to run this script:
    
        * Test run: fab run_script:scripts.fix_nominative_reporters.main
            - prints ~70,000 lines of intended actions
        * Actual run: fab run_script:scripts.fix_nominative_reporters.main,dry_run=false
        * Pre-run edits (already applied): fab run_script:scripts.fix_nominative_reporters.manual_pre_edits
"""


def manual_pre_edits():
    """
        These fixes were determined from inspecting the initial output of main() for error messages.
    """
    with EditLog(
        description='Swap reporter and volume number for NOTALEPH001894 (was 26 S.C.L. (McMul.)) '
        'and NOTALEPH001893 (was 7 S.C. Eq. (McCord Eq.))'
    ).record():
        v1 = VolumeMetadata.objects.get(barcode='NOTALEPH001894', reporter__short_name='S.C.L. (McMul.)')
        v2 = VolumeMetadata.objects.get(barcode='NOTALEPH001893', reporter__short_name='S.C. Eq. (McCord Eq.)')
        new_r1 = v2.reporter
        new_volnum1 = v2.volume_number
        new_r2 = v1.reporter
        new_volnum2 = v1.volume_number

        v1.volume_number = new_volnum1
        v1.set_reporter(new_r1)

        v2.volume_number = new_volnum2
        v2.set_reporter(new_r2)

    with EditLog(
         description='Combine reporters 909 and 1075 into just 1075, and 1076 and 919 into just 919. '
         'This combines the first and second run of S.C.L. (Rich.) and S.C. Eq. (Rich. Eq.), respectively. '
         'They are combined as they use the same numbering sequence -- see '
         'https://www.sccourts.org/courtreg/displayRule.cfm?ruleID=268.0&subRuleID=&ruleType=APP'
    ).record():
        for first_id, second_id in ((909, 1075), (1076, 919)):
            r1 = Reporter.objects.get(id=first_id)
            r2 = Reporter.objects.get(id=second_id)
            r2.start_year = r1.start_year
            r2.volume_count += r1.volume_count
            r2.hollis += r1.hollis
            r2.save()
            for v in r1.volumes.all():
                v.set_reporter(r2)
            r1.delete()

    with EditLog(
        description='Mark 32044078662582 (3A Tenn. (Cooke)) as a duplicate of (the appendix to) 32044078663788 (158 Tenn.). '
        'See E. Lucy Ogden, A Note on 3A Tenn. Reports, 19 Tenn. L. Rev. 74 (1945), explaining that former was separately published '
        'for attorneys who did not subscribe to latter and should not be cited.'
    ).record():
        old = VolumeMetadata.objects.get(pk='32044078662582')
        new = VolumeMetadata.objects.get(pk='32044078663788')
        if not old.duplicate_of == new:
            old.set_duplicate(True, new)

    with EditLog(
        description='Update case citation from "50 50 Ky. (B. Mon.) 178 183" to "50 Ky. (B. Mon.) 183".'
    ).record():
        c = Citation.objects.get(cite="50 50 Ky. (B. Mon.) 178 183")
        c.cite = "50 Ky. (B. Mon.) 183"
        c.save()

# these volumes have the correct reporters, but the existing case citations are wrong:
cite_overrides = {
    # volume.barcode: [wrong_old_prefix, fixed_old_prefix]
    "32044049389018": ["59 Allen", "5 Cush."],
    "32044106247190": ["6 Allen", "6 Cush."],
    "32044078699394": ["8 S.C.L. (Mill Const.)", "8 Mill"],
    "32044078699386": ["9 S.C.L. (Mill Const.)", "9 Mill"],
    "32044078699527": ["43 S.C.L. (3 Rich.)", "9 Rich."],
    "32044103138079": ["87 U.S. (1 Wall.)", "20 Wall."],
    "32044103138137": ["89 U.S. (1 Wall.)", "22 Wall."],
}

def alphanum(s):
    return re.sub(r'[^a-zA-Z0-9]', '', s)

def main(dry_run='true'):

    # handle each line from manual_fixes.csv
    fixes = csv.DictReader(Path(__file__).parent.joinpath('manual_fixes.csv').open())
    for fix in fixes:
        if not fix['official']:
            continue

        with EditLog(
            description='Mark reporter %s as nominative for reporter %s' % (fix['short'], fix['official'])
        ).record():
            nominative_reporter = Reporter.objects.get(id=fix['id'])
            print("Updating %s" % nominative_reporter)
            if nominative_reporter.is_nominative:
                print("- skipping, already fixed")
                continue

            ## associate nominative reporter with official reporter

            if fix['official'].isnumeric():
                official_reporter = Reporter.objects.get(id=fix['official'])
            else:
                official_reporter = Reporter.objects.get(short_name=fix['official'])
            nominative_reporter.nominative_for = official_reporter
            nominative_reporter.is_nominative = True
            nominative_reporter.short_name = fix['nominative']

            print("- update %s to be nominative for %s" % (nominative_reporter, official_reporter))
            if dry_run == 'false':
                nominative_reporter.save()

            ## prepare to process each volume in nominative reporter

            print("- update volumes")
            volumes = natsorted(nominative_reporter.volumes.filter(duplicate=False).order_by('volume_number'), key=lambda v: v.volume_number)
            last_volume_numbers = []
            volume_index = 0

            # the 'official offset' column indicates how official volume numbers are derived from nominative volume numbers.
            # it can be in two formats
            official_offsets = {}
            official_offset_default = None
            if ',' in fix['official offset']:
                # the first format is a set of ranges, like "1-2: 18, 3-14: 24", meaning volumes 1 and 2 were renumbered
                # to 18, 19, etc., and 3-14 were renumbered to 24, 25, etc. Parse this into a dict like {1: 18, 2: 19, 3: 24, 4: 25 ...}
                for offset_range in fix['official offset'].split(', '):
                    start_stop, offset = offset_range.split(': ')
                    start, stop = start_stop.split('-')
                    offset = int(offset)
                    for i, vol_num in enumerate(range(int(start), int(stop)+1)):
                        official_offsets[vol_num] = offset + i
            else:
                # the second format is just a single number
                official_offset_default = int(fix['official offset'])

            ## process each volume

            for volume in volumes:

                ## update volume to have correct volume_number, nominative_volume_number, and references to its official reporter and its nominative reporter

                volume_number = int(volume.volume_number)
                if volume_number in last_volume_numbers:
                    print(" - WARNING: duplicate volume number %s" % volume_number)
                else:
                    volume_index += 1
                expected_official_volume_number = official_offsets[volume_index] if official_offsets else volume_index + official_offset_default - 1
                expected_nominative_volume_number = volume_index
                if volume_number != expected_nominative_volume_number and volume_number != expected_official_volume_number:
                    print(" - ERROR: Unexpected volume number: %s" % volume_number)
                    continue
                last_volume_numbers = [expected_official_volume_number, expected_nominative_volume_number]
                volume.nominative_volume_number = expected_nominative_volume_number
                volume.volume_number = expected_official_volume_number
                volume.reporter = official_reporter
                volume.nominative_reporter = nominative_reporter

                print(" - update %s to %s,%s" % (volume_number, volume.volume_number, volume.nominative_volume_number))
                if dry_run == 'false':
                    volume.save()

                ## update citations for each case in volume

                # Do some sanity checking here -- if the case is supposed to end up with official citation "5 Mass. 123"
                # and nominative citation "1 Bar 123", then we expect the current official citation to start with either
                # a "1" or "5", followed by either "Mass." or "Bar" or "Mass. (Bar)".

                # figure out what we expect:
                print("  - update cases")
                official_cite_prefix = "%s %s " % (volume.volume_number, official_reporter.short_name)
                nominative_cite_prefix = "%s %s " % (volume.nominative_volume_number, nominative_reporter.short_name)
                expected_short_names = [official_reporter.short_name, nominative_reporter.short_name, "%s (%s)" % (official_reporter.short_name, nominative_reporter.short_name)]
                expected_prefixes = [alphanum("%s %s" % (n, prefix)) for n in [expected_official_volume_number, expected_nominative_volume_number] for prefix in expected_short_names]
                if volume.barcode in cite_overrides:
                    wrong_old_prefix, fixed_old_prefix = cite_overrides[volume.barcode]
                else:
                    wrong_old_prefix, fixed_old_prefix = None, None

                for case in volume.case_metadatas.prefetch_related('citations'):

                    # check if existing cite matches expectations:
                    official_cite = next(c for c in case.citations.all() if c.type == 'official')
                    old_official_cite = official_cite.cite
                    old_prefix, old_page_num = old_official_cite.rsplit(' ', 1)
                    if fixed_old_prefix and wrong_old_prefix == old_prefix:
                        old_prefix = fixed_old_prefix
                    if alphanum(old_prefix) not in expected_prefixes:
                        print("   - ERROR: cite %s not expected" % old_official_cite)
                        continue

                    # create new official and nominative cites:
                    official_cite.cite = official_cite_prefix + old_page_num
                    nominative_cite = deepcopy(official_cite)
                    nominative_cite.cite = nominative_cite_prefix + old_page_num
                    nominative_cite.type = 'nominative'
                    nominative_cite.pk = None
                    print("   - update %s to %s and %s" % (old_official_cite, official_cite, nominative_cite))
                    if dry_run == 'false':
                        official_cite.save()
                        nominative_cite.save()

            if dry_run != 'false':
                raise EditLog.Cancel