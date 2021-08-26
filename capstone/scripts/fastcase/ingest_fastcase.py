import csv
import gzip
import re
from collections import defaultdict
import html
import json
import jsonschema
from datetime import date
from pathlib import Path
import xmltodict
from eyecite.models import FullCitation
from natsort import natsort_keygen

from django.conf import settings
from django.db.models import Q

from capdb.models import CaseMetadata, Court, Reporter, VolumeMetadata, Citation, Jurisdiction, FastcaseImport, EditLog
from fabfile import update_reporter_years
from scripts.extract_cites import extract_whole_cite
from scripts.fastcase.format_fastcase import format_fastcase_html_from_parts, strip_tags
from scripts.helpers import group_by, alphanum_lower, jurisdiction_translation_long_name, postal_states

r"""
    This file imports an export of cases from Fastcase.
    
    Cases are assumed to be unzipped in some base_dir, with a reporter-volume layout like this:
    
    - <base_dir>
        - A3d
            - 30
                - somecase.xml
            
    Entry points:
    
    - fab run_script:scripts.fastcase.ingest_fastcase,pack_volumes,<base_dir>
        This command reformats the xml files in each volume folder into a single file, cases.json.gz, for faster ingest.
        This should be run first when dealing with a new batch of documents to ingest.
    - fab run_script:scripts.fastcase.ingest_fastcase,dump_html,<base_dir>,<reporter/volume/case.xml>
        Dump HTML for a single case, useful for debugging
    - fab run_script:scripts.fastcase.ingest_fastcase,<batch_name>,<base_dir>
        Once pack_volumes has been run, this actually ingests cases and creates:
            - CaseMetadata
            - CaseInitialMetadata
            - Citation
            - Court
            - CaseBodyCache
        This also writes <base_dir>/statistics.json with reports about difficulties encountered along the way
        To run only a particular subfolder:
            - fab run_script:scripts.fastcase.ingest_fastcase,...,reporter_filter=P3d
            - fab run_script:scripts.fastcase.ingest_fastcase,...,reporter_filter=P3d,volume_filter=31
    - Steps after ingest is complete:
        - fab refresh_case_body_cache:if_missing=1
            to build case.body_cache for all new cases. This has to run after ingest is over to make sure we
            find citations between new cases.
        - fab update_reporter_years
            Necessary only if script is terminated before a reporter finishes importing
        
    Notes about Fastcase import:
    
    - U.S. cases should supersede S.Ct. cases. Currently they are just both imported.
    - N.Y.S. cases are duplicated in A.3d. Skip those cases there, as well as skipping entire NYS3d dir for now.
      NYS wasn't included in the initial CAP import.
    - CAP has paragraph IDs that are unique per volume. For Fastcase, we just generate paragraph IDs that are unique
      per-case.
      
    Todo later:
    - check case names against [a-zA-Z0-9.,& \-\'"/$¢#ŒǢӔÆœӕæǣŞÇÓÖÍÁÀÜĪÉŠğóöòōøôӧõñńãāâáàåäúüũûìíïēéèêĕëçčćšśž()\[\]—§:;·+*★@?%®™!_⅙¼½¾⅔⅞²³°¶º|^]
    - <pre> tags with tables -- test_data/zips/fastcase/SE2d/655/655SE2d10_1.xml test_data/zips/fastcase/NE2d/989/989ne2d1109.xml
    - copy extra cites from duplicate cases
    - missing spaces around "v." -- "STATE of Connecticutv.Richard ANNULLI."
    - _opinionstart titles like "OPINION" could be labeled / used somehow
    - do something with opinions that just have head matter and no opinion
        in some cases it would make sense to use the final line as the opinion text, like SCt/134/134sct985_2.xml
        but this doesn't work with footnotes, e.g. A3d/50/50a3d607_29.xml
"""


### helpers ###

default_base_dir = Path(settings.BASE_DIR) / 'test_data' / 'fastcase'


def get_dirs(path: Path):
    """Get all visible directories in path."""
    for sub_path in sorted(path.iterdir()):
        if sub_path.is_dir() and not sub_path.name.startswith('.'):
            yield sub_path


def normalize_digits(s):
    return re.sub(r'\d+', '#', s)


def get_digits(s):
    return re.sub(r'[^0-9]', r'', s)


def unescape(s):
    if s:
        return html.unescape(s)
    return s


def skip_case(reporter_dir, case):
    return (
        # skip cases where file name doesn't include reporter directory name. this avoids duplicates like
        # "P3d/387/212 Cal.Rptr.3d 620-1_Replace.xml"
        alphanum_lower(reporter_dir.name) not in alphanum_lower(case["FileName"]) or
        # cases without casehtml or decisiondate are invalid
        not case['CaseHtml'] or
        not case['DecisionDate']
    )

# if a court abbreviation starts with one of these strings, it is federal:
_guess_jurisdiction_federal_prefixes = ('D. ', 'N.D. ', 'S.D. ', 'E.D. ', 'W.D. ', 'Bankr.')

# guess a state name based on the court abbreviation containing one of the keys in this dict:
_guess_jurisdiction_state_strings = {
    # add Bluebook abbreviations, like "Mass.": "Massachusetts":
    **jurisdiction_translation_long_name,
    # add postal abbreviations, like "MA": "Massachusetts":
    **postal_states,
    # add state names, like "Massachusetts": "Massachusetts":
    **{v: v for v in jurisdiction_translation_long_name.values()},
    # special cases from previous ingest data:
    'Ia.': 'Iowa',
    'Ok.': 'Oklahoma',
}

def guess_jurisdiction(abbv):
    """Guess the state name for a court abbreviation."""
    if any(abbv.startswith(s) for s in _guess_jurisdiction_federal_prefixes):
        return ['United States']
    else:
        abbv += '.'  # otherwise we fail for court "Va"
        return [v for k, v in _guess_jurisdiction_state_strings.items() if k in abbv]

### pack xml to json ###

_schema = None
_validator = None


def validate_json(json_data):
    global _schema, _validator

    if not _validator:
        _schema = json.loads(Path(__file__).parent.joinpath('ingest_fastcase.schema.json').read_text())
        _validator = jsonschema.validators.validator_for(_schema)(_schema)

    return _validator.validate(json_data, _schema)


def read_fastcase_xml_file(case_path):
    """ Convert fastcase XML to a json dict, validating against a schema and normalizing some irregularities."""
    # validate case
    case_text = case_path.read_text()
    # fix unescaped A tags
    case_text = re.sub(r'<(A [^>]+|/A)>', r'&lt;\1&gt;', case_text)
    # fix decided tags in middle of HeaderHtml
    case_text = case_text.replace("<decided />", "&lt;decided /&gt;")
    # fix that one case with closing tags outside (SE2d/634/634SE2d675_1.xml)
    case_text = case_text.replace(
        "\n\t</HeaderHtml>&lt;/CENTER&gt;&lt;/B&gt;&lt;/P&gt;",
        "&lt;/CENTER&gt;&lt;/B&gt;&lt;/P&gt;</HeaderHtml>")
    case_dict = xmltodict.parse(case_text, force_list=('Citation', 'DocketNumber'))['Case']
    if "OriginalDocumentID" in case_dict and not case_dict["OriginalDocumentID"]:
        del case_dict["OriginalDocumentID"]
    try:
        validate_json(case_dict)
    except Exception as e:
        print(f"ingesting {case_path}")
        print(e)
        return None

    # light cleanup
    case_dict["CourtName"] = unescape(case_dict["Jurisdiction"]["CourtName"])
    case_dict["CourtAbbreviation"] = unescape(case_dict["Jurisdiction"]["CourtAbbreviation"])
    del case_dict["Jurisdiction"]
    if "Citations" in case_dict:
        case_dict["Citations"] = case_dict["Citations"]["Citation"]
        if case_dict["Citations"] == [None]:
            case_dict["Citations"] = []
        case_dict["Citations"] = [{k: unescape(v) for k, v in c.items()} for c in case_dict["Citations"]]
    else:
        case_dict["Citations"] = []
    if case_dict.get("DocketNumbers"):
        case_dict["DocketNumbers"] = case_dict["DocketNumbers"]["DocketNumber"]
        if case_dict["DocketNumbers"] == [None]:
            case_dict["DocketNumbers"] = []
        case_dict["DocketNumbers"] = [unescape(d) for d in case_dict["DocketNumbers"]]
    else:
        case_dict["DocketNumbers"] = []
    case_dict.setdefault("LawyerHeader", None)
    case_dict.setdefault("Author", None)
    case_dict.setdefault("DecisionDate", None)
    case_dict["FileName"] = case_path.name
    for k in ("ShortName", "Author", "PartyHeader", "LawyerHeader"):
        case_dict[k] = unescape(case_dict[k])

    return case_dict


def pack_volumes(base_dir=default_base_dir, recreate=False):
    for reporter_dir in get_dirs(base_dir):
        for volume_dir in get_dirs(reporter_dir):
            json_path = volume_dir / 'cases.json.gz'
            if not recreate and json_path.exists():
                continue

            print(f"packing {volume_dir}")

            cases = []
            errors = False
            for case_path in sorted(volume_dir.glob('*.xml')):
                case_dict = read_fastcase_xml_file(case_path)
                if case_dict:
                    cases.append(case_dict)
                else:
                    errors = True

            # write valid volumes to file
            if cases and not errors:
                try:
                    with gzip.open(json_path, 'wb') as f:
                        f.write(json.dumps(cases, indent=2, ensure_ascii=False).encode('utf8'))
                except BaseException:
                    # don't leave broken gzips around after ctrl-C
                    json_path.unlink(missing_ok=True)
                    raise


### directory stuff ###


def get_reporters(base_dir, reporter_filter):
    out = []
    reporters = group_by(Reporter.objects.all(), lambda r: alphanum_lower(r.short_name))

    # filter dirs by reporter_filter
    if reporter_filter:
        reporter_dir = Path(base_dir) / reporter_filter
        if not reporter_dir.exists():
            raise ValueError(f"Unknown reporter dir: {reporter_dir}")
        reporter_dirs = [reporter_dir]
    else:
        reporter_dirs = get_dirs(base_dir)

    for reporter_dir in reporter_dirs:
        reporter_options = reporters[alphanum_lower(reporter_dir.name)]
        if len(reporter_options) != 1:
            raise ValueError(f"Unrecognized reporter {reporter_dir.name}")
        out.append((reporter_dir, reporter_options[0]))

    return out


def get_volumes(reporter_dir, volume_filter):
    volumes = []

    # filter dirs by volume_filter
    if volume_filter:
        volume_dir = reporter_dir / volume_filter
        if not volume_dir.exists():
            raise ValueError(f"Unknown reporter dir: {volume_dir}")
        volume_dirs = [volume_dir]
    else:
        volume_dirs = get_dirs(reporter_dir)

    for volume_dir in volume_dirs:
        if not (volume_dir / 'cases.json.gz').exists():
            continue
        volume_number = volume_dir.name
        if not volume_number.isdigit():
            raise ValueError(f"unexpected volume number in dir name: {volume_dir}")
        volumes.append((volume_dir, volume_number))

    return volumes


def filter_cases(cases, case_filter):
    if not case_filter:
        return cases
    return [c for c in cases if c["FileName"] == case_filter]


def split_filter(filter):
    """Split a string like "A3d" or "A3d/28" or "A3d/28/28a3d1.xml" into three parts, returning None for parts not included."""
    return (filter.split("/") + [None, None])[:3]


def dump_html(case_path):
    """Dump CAP html from a Fastcase file."""
    fastcase_data = read_fastcase_xml_file(Path(case_path))
    cites = []
    for cite_parts in fastcase_data['Citations']:
        cites.append(Citation(cite=" ".join((cite_parts["Volume"], cite_parts["Reporter"], cite_parts["Page"])), type="parallel"))
    cites[0].type = "official"
    result = format_fastcase_html_from_parts(CaseMetadata(), cites, fastcase_data)
    print(result['html'])


def main(batch=None, base_dir=default_base_dir, reporter_filter=None, volume_filter=None):
    """
        Main entry point -- ingest cases.
    """
    if not batch:
        batch = str(date.today().year)

    # build a lookup table of courts by name_abbreviation, sorted by number of cases for that court.
    # use a cached csv to avoid doing a big join every time:
    # \copy (select ct.id, ct.name, ct.name_abbreviation, count(*) from capdb_court ct, capdb_casemetadata c where c.court_id=ct.id group by ct.id) to '/home/jcushman/court_counts.csv' with csv
    courts = group_by(Court.objects.all(), lambda c: c.name_abbreviation)
    with open(Path(__file__).parent.joinpath("court_counts.csv")) as f:
        court_counts = {row[0]: row[3] for row in csv.reader(f)}
    for court_list in courts.values():
        for court in court_list:
            court.case_count = court_counts.get(court.id, 0)
        court_list.sort(key=lambda c: c.case_count, reverse=True)

    jurisdictions_by_name = {j.name_long: j for j in Jurisdiction.objects.all()}

    # scan all reporters and volumes to make sure folder layout maps to our database:
    reporters = [(reporter_dir, reporter, get_volumes(reporter_dir, volume_filter)) for reporter_dir, reporter in get_reporters(base_dir, reporter_filter)]

    # lookup table of any existing volumes matching the ones we're importing
    query = Q()
    for _, reporter, volumes in reporters:
        for volume_number in volumes:
            query |= Q(reporter=reporter, volume_number=volume_number)
    existing_volumes = group_by(
        VolumeMetadata.objects.filter(query),
        lambda v: (v.reporter, v.volume_number))

    cases_processed = 0

    new_courts = {}

    for reporter_dir, reporter, volumes in reporters:
        # just skip N.Y.S. 3d for now
        if reporter_dir.name == 'NYS3d':
            continue
        reporter_name_lower = reporter_dir.name.lower()
        for volume_dir, volume_number in volumes:
            print(f"ingesting {volume_dir}")
            if (reporter, volume_number) in existing_volumes:
                # Note we can't currently attempt a second ingest of an already ingested volume.
                # Would need to figure out how to have the duplicate-case logic work
                # even if some of the cases are already in the db and thus shouldn't be recreated.
                # Or you can delete the entire volume ...
                print("- skipping, already ingested")
                continue
                # volume = existing_volumes[(reporter, volume_number)]
            else:
                barcode = re.sub(r'[. ]', '', reporter.short_name) + '_' + volume_number
                volume = VolumeMetadata(
                    barcode=barcode,
                    reporter=reporter,
                    volume_number=volume_number,
                    notes=f"Ingested from Fastcase, batch {batch}",
                    ingest_status='ingested',
                    contributing_library="Fastcase",
                )

            with gzip.open(volume_dir / 'cases.json.gz', 'rb') as f:
                cases = json.loads(f.read().decode('utf8'))

            cases_to_create = []
            volume_new_courts = []

            # record statistics about ingest problems
            volume_stats = {
                "file_name_patterns": defaultdict(int),
                "unknown_courts": defaultdict(set),
                "invalid_jurisdiction_courts": defaultdict(set),
                "ambiguous_courts": defaultdict(set),
                "courts": defaultdict(set),
                "unrecognized_cites": defaultdict(int),
                "corrections": [],
                "unknown_cite_types": set(),
                "duplicate_cites": [],
                "no_official_cite": [],
                "unrecognized_dates": defaultdict(set),
                "collisions": [],
            }

            for case_dict in cases:
                cases_processed += 1

                case_path = "/".join([reporter_dir.name, volume_dir.name, case_dict["FileName"]])

                if skip_case(reporter_dir, case_dict):
                    continue

                # log filename pattern
                file_name_pattern = normalize_digits(case_dict["FileName"].replace(reporter_name_lower, 'REP'))
                volume_stats["file_name_patterns"][file_name_pattern] += 1

                # get case first page
                # first page is usually the number that comes immediately after reporter_name_lower in the file name
                case_name_lower = alphanum_lower(case_dict["FileName"])
                case_name_suffix = case_name_lower.split(reporter_name_lower, 1)[1]
                m = re.match(r'\d+', case_name_suffix)
                first_page = m[0]
                first_page_order = int(first_page)

                # make case object
                case = {
                    'case_id': f'FC:{case_path}',
                    'name_abbreviation': case_dict['ShortName'],
                    # PartyHeader can be empty, e.g. NE2d/939/939ne2d586.xml
                    # Could possibly be recovered from text; unclear if this indicates case shouldn't be ingested
                    'name': strip_tags(case_dict['PartyHeader'] or case_dict['ShortName']),
                    'volume': volume,
                    'reporter': reporter,
                    'first_page': first_page,
                    # first_page_order is incorrect, since it should include front matter, but at least can be used for sorting
                    'first_page_order': first_page_order,
                    # last_page values are likely wrong. we will attempt to update them below based on page number extraction
                    'last_page': first_page,
                    'last_page_order': first_page_order,
                }

                # court and jurisdiction
                court_abbv = case_dict['CourtAbbreviation']
                court_name = case_dict['CourtName'] or court_abbv
                # court name fixups
                court_name = re.sub('Hawai[^a-zA-Z]+i', 'Hawaii', court_name)  # Hawai‘i, Hawai § i ...
                court_name = court_name.rstrip('.')
                # court abbreviation fixups
                court_abbv = re.sub(r'\s+', ' ', court_abbv)  # fix "Wash.  App."
                court_abbv = re.sub(r'([a-z]\.)([A-Z])', r'\1 \2', court_abbv)  # fix "Pa.Ct.Jud.Disc." -> Pa. Ct. Jud. Disc.
                if ".App." in court_abbv:
                    court_abbv = court_abbv.replace(".App.", ". App.")
                if court_abbv.endswith("App.") or (court_abbv not in courts and court_abbv+" Ct." in courts):
                    court_abbv += " Ct."
                court_options = courts.get(court_abbv, [])
                court_key = court_abbv + ":" + "|".join(c.name for c in court_options)
                if not court_options:
                    volume_stats["unknown_courts"][court_abbv].add(court_name)
                    new_courts_key = (court_name, court_abbv)
                    if new_courts_key not in new_courts:
                        jurisdiction_guesses = guess_jurisdiction(court_abbv)
                        if len(jurisdiction_guesses) != 1:
                            volume_stats["invalid_jurisdiction_courts"][court_abbv].add(court_name)
                            continue
                        jurisdiction = jurisdictions_by_name[jurisdiction_guesses[0]]
                        new_court = Court(name=court_name, name_abbreviation=court_abbv, jurisdiction=jurisdiction)
                        new_courts[new_courts_key] = new_court
                        volume_new_courts.append(new_court)
                    court_options = [new_courts[new_courts_key]]
                elif len(court_options) > 1:
                    volume_stats["ambiguous_courts"][court_key].add(court_name)
                else:
                    volume_stats["courts"][court_key].add(court_name)
                # choose the court with most existing cases
                case['court'] = court_options[0]
                case['jurisdiction'] = court_options[0].jurisdiction

                # docket number
                docket_numbers = case_dict['DocketNumbers']
                if docket_numbers is not None:
                    case['docket_numbers'] = docket_numbers
                    case['docket_number'] = "; ".join(docket_numbers)

                # citations
                citations = []
                official_volume_reporter = None
                for cite_parts in case_dict['Citations']:
                    if cite_parts["Reporter"] in {"SERB"}:
                        # unknown cite formats -- 3 cases have "2013 SERB 4", like NE2d/998/998ne2d1124.xml
                        continue
                    if cite_parts["Reporter"].startswith('-'):
                        cite_sep = ''
                    elif cite_parts["Reporter"] in ('NMCA', 'NMSC'):
                        cite_sep = '-'
                    else:
                        cite_sep = ' '
                    cite_str = cite_sep.join((cite_parts["Volume"], cite_parts["Reporter"], cite_parts["Page"]))

                    eyecite_cite = extract_whole_cite(cite_str, require_classes=(FullCitation,))
                    if not eyecite_cite:
                        volume_stats["unrecognized_cites"][normalize_digits(cite_str)] += 1
                        continue
                    corrected_cite = eyecite_cite.corrected_citation()
                    normalized_cite = alphanum_lower(corrected_cite)

                    # skip duplicates
                    if any(c['attrs']['cite'] == corrected_cite for c in citations):
                        continue

                    cite_type = eyecite_cite.all_editions[0].reporter.cite_type
                    if cite_type == 'journal':
                        volume_stats["corrections"].append([case_path, "skipping journal cite", cite_str])
                        continue

                    if re.sub(r'[ .]', '', cite_parts["Reporter"]) == reporter_dir.name:
                        cap_type = "official"
                        official_volume_reporter = f'{cite_parts["Volume"]} {cite_parts["Reporter"]}'
                        # if we find official cite, replace first_page from file name with that --
                        # fixes issue with file names like 781NW2d7062010WIApp50.xml
                        case['first_page'] = case['last_page'] = first_page = cite_parts["Page"]
                        case['first_page_order'] = case['last_page_order'] = first_page_order = int(first_page)
                    elif cite_type in ('state', 'federal', 'neutral'):
                        cap_type = "parallel"
                    elif 'regional' in cite_type:
                        cap_type = "parallel"
                    elif 'specialty' in cite_type:
                        cap_type = "vendor"
                    else:
                        volume_stats["unknown_cite_types"].add(cite_type)
                        continue

                    citations.append({
                        'attrs': {
                            'cite': corrected_cite,
                            'normalized_cite': normalized_cite,
                            'rdb_cite': corrected_cite,
                            'rdb_normalized_cite': normalized_cite,
                            'type': cap_type,
                            'category': cite_parts.get('Suffix'),
                        },
                        'eyecite_type': cite_type,
                        'reporter': eyecite_cite.corrected_reporter(),
                    })

                if not citations:
                    volume_stats["corrections"].append([case_path, "skipping case, no citations"])
                    continue

                # try to guess last_page from page numbers like "[440 P.3d 123]"
                if official_volume_reporter:
                    matches = re.findall(rf'\[{official_volume_reporter} (\d+)\]', case_dict['HeaderHtml']+case_dict['CaseHtml'])
                    if matches:
                        last_page_order = max(int(m) for m in matches)
                        if last_page_order > first_page_order:
                            case['last_page'] = str(last_page_order)
                            case['last_page_order'] = last_page_order

                # check for duplicate cites
                # 1696 cases have duplicate citations for the same reporter.
                # we choose to keep the natural-sorted highest citation, on the principle that cases can only
                # cite earlier and not later
                if len(citations) > len(set(c['reporter'] for c in citations)):
                    kept_reporters = set()
                    citations.sort(key=natsort_keygen(key=lambda c: c['attrs']['cite']), reverse=True)
                    filtered_cites = []
                    for cite in citations:
                        if cite['reporter'] not in kept_reporters:
                            kept_reporters.add(cite['reporter'])
                            filtered_cites.append(cite)
                    citations = filtered_cites
                    volume_stats["duplicate_cites"].append([case_path, [c['cite'] for c in citations]])

                # check for cases having both appeals court and supreme court cites
                # keep only the supreme court cite
                # e.g. ('Ga.', 'Ga. App.'), ('Mass.', 'Mass. App. Ct.'), 'N.C.', 'N.C. App.', 'Ohio', 'Ohio App. #d', ('UT', 'UT App'), 'WI', 'WI App'
                state_cites = [c for c in citations if c['eyecite_type'] == 'state']
                if len(state_cites) > 1:
                    to_remove = []
                    for c1 in state_cites:
                        for c2 in state_cites:
                            if c1 == c2:
                                continue
                            if c2['reporter'].startswith(c1['reporter']+' App'):
                                to_remove.append(c2)
                    for cite in to_remove:
                        citations.remove(cite)

                # check for cases with no official cite
                if not any(c['attrs']['type'] == 'official' for c in citations):
                    volume_stats["no_official_cite"].append([case_path]+[c['attrs']['cite'] for c in citations])
                    citations[0]['attrs']['type'] = 'official'

                # decision date
                decision_date = case_dict['DecisionDate']
                if decision_date:
                    # special case P3d/256/256p3d1131.xml - 2011-.04-28
                    m = (
                            re.match(r'(?P<month>\d{1,2})-(?P<day>\d{1,2})-(?P<year>\d{4})$', decision_date) or
                            re.match(r'(?P<year>\d{4})-\.?(?P<month>\d{1,2})-(?P<day>\d{1,2})$', decision_date)
                    )
                    if m:
                        case['decision_date_original'] = f"{m['year']}-{m['month'].zfill(2)}-{m['day'].zfill(2)}"
                if not case.get('decision_date_original'):
                    volume_stats["unrecognized_dates"].add(decision_date)
                    continue

                cases_to_create.append({
                    'attrs': case,
                    'citations': citations,
                    'path': case_path,
                    'orig': case_dict,
                })

            # short circuit if whole volume was already ingested
            if not cases_to_create:
                continue

            ## check for internal duplicates
            duplicates_to_create = []
            removed_paths = set()

            # check for internal duplicates
            cases_by_cite = defaultdict(list)
            for case in cases_to_create:
                attrs = case['attrs']
                for cite in case['citations']:
                    cases_by_cite[(attrs['name_abbreviation'].lower(), get_digits(attrs['docket_number']), cite['attrs']['rdb_cite'])].append(case)
            for cases in cases_by_cite.values():
                cases = [c for c in cases if c['path'] not in removed_paths]
                if len(cases) < 2:
                    continue
                # sort by length in reverse so we pick the longest,
                # then (arbitrarily) by case path so we always pick the same one for duplicates
                cases.sort(key=lambda c: (len(c['orig']['CaseHtml']), c['path']), reverse=True)
                first_case, dupe_cases = cases[0], cases[1:]
                first_case_normalized = re.sub(r'[_\-]\d+', r'', first_case['orig']["FileName"], count=1)
                for case in dupe_cases:
                    # when two cases appear on the same page, they have predictable file names like
                    # 737NW2d433_1.xml - 737NW2d433_2.xml or 87 N.E.3d 9-1.xml - 87 N.E.3d 9-2.xml
                    # if two cases have matching names except for those appendixes, treat them as non-duplicates:
                    if re.sub(r'[_\-]\d+', r'', case['orig']["FileName"], count=1) == first_case_normalized:
                        continue

                    volume_stats["corrections"].append([case['path'], "skipping duplicate file", first_case['path']])
                    case['duplicate_of'] = first_case
                    cases_to_create.remove(case)
                    duplicates_to_create.append(case)
                    removed_paths.add(case['path'])

            ## check for database duplicates

            # don't check for duplicates with U.S. reporter. we don't want to import entire regionals when we have all but one
            # state, but we do want to import U.S. reporter when it comes out after S.Ct. for the same case.
            if reporter.short_name != 'U.S.':

                # group by cite
                cites_by_type = {'cite': [], 'normalized_cite': [], 'rdb_cite': [], 'rdb_normalized_cite': []}
                new_cases_by_cite = {c: defaultdict(list) for c in cites_by_type}
                for case in cases_to_create:
                    for cite in case['citations']:
                        cite_attrs = cite['attrs']
                        for k in cites_by_type:
                            cites_by_type[k].append(cite_attrs[k])
                            new_cases_by_cite[k][cite_attrs[k]].append(case)

                # find collisions
                db_cases = CaseMetadata.objects.in_scope().filter(
                    Q(citations__cite__in=cites_by_type['cite']) |
                    Q(citations__normalized_cite__in=cites_by_type['normalized_cite']) |
                    Q(citations__rdb_cite__in=cites_by_type['rdb_cite']) |
                    Q(citations__rdb_normalized_cite__in=cites_by_type['rdb_normalized_cite'])
                ).prefetch_related('citations')
                collisions = defaultdict(lambda: {'new_case': None, 'db_cases': set()})
                for db_case in db_cases:
                    for db_cite in db_case.citations.all():
                        for k in cites_by_type:
                            cite_str = getattr(db_cite, k)
                            if cite_str in new_cases_by_cite[k]:
                                for new_case in new_cases_by_cite[k][cite_str]:
                                    if new_case['path'] not in removed_paths and get_digits(new_case['attrs']['docket_number']) == get_digits(db_case.docket_number):
                                        # is a duplicate
                                        new_case['duplicate_of'] = db_case
                                        cases_to_create.remove(new_case)
                                        duplicates_to_create.append(new_case)
                                        removed_paths.add(new_case['path'])
                                    collision = collisions[new_case['path']]
                                    collision['new_case'] = new_case
                                    collision['db_cases'].add(db_case)

                # record all possible collisions
                for collision in collisions.values():
                    c = collision["new_case"]
                    volume_stats["collisions"].append([
                        {
                            **{k: c['attrs'][k] for k in ["name", "name_abbreviation", "decision_date_original", "docket_number"]},
                            'cites': [cite['attrs']['rdb_cite'] for cite in c['citations']],
                            'path': c['path'],
                        },
                        [
                            {
                                "name": d.name, "name_abbreviation": d.name_abbreviation, "decision_date_original": d.decision_date_original,
                                "docket_number": d.docket_number,
                                "cites": [cite.rdb_cite for cite in d.citations.all()]
                            }
                            for d in collision['db_cases']
                        ]
                    ])

            # save volume
            with EditLog(description=f"Ingest Fastcase volume {reporter_dir.name}/{volume_dir.name}").record():
                # save new cases
                if cases_to_create:
                    # save volume
                    # store start and stop years in spine_start_year as well for now, because that's what's
                    # served in the volume API, even though these aren't really from the spine
                    years = [int(c['attrs']['decision_date_original'][:4]) for c in cases_to_create]
                    volume.start_year = volume.spine_start_year = min(*years, volume.start_year or 9999)
                    volume.end_year = volume.spine_end_year = max(*years, volume.end_year or 0)
                    # store volume_stats under `xml_metadata`, using json to change sets to lists
                    volume.xml_metadata = json.loads(json.dumps(volume_stats, ensure_ascii=False, default=list))
                    volume.save()

                    # save courts
                    if volume_new_courts:
                        # don't use bulk_create because courts need save() method to find a slug
                        for court in volume_new_courts:
                            court.save()

                    # save non-duplicate cases
                    cites_to_create = []
                    fastcase_imports_to_create = []
                    to_sync = []
                    for new_case in cases_to_create:
                        new_case['db'] = db_case = CaseMetadata(source='Fastcase', batch=batch, **new_case['attrs'])
                        db_case.save()
                        to_sync.append(db_case)
                        cites_to_create.extend(Citation(case=db_case, **c['attrs']) for c in new_case['citations'])
                        fastcase_import = FastcaseImport(case=db_case, data=new_case['orig'], path=new_case['path'], batch=batch)
                        db_case.fastcase_import = fastcase_import
                        fastcase_imports_to_create.append(fastcase_import)
                    Citation.objects.bulk_create(cites_to_create)
                    CaseMetadata.update_frontend_urls(c.cite for c in cites_to_create if c.type == 'official')
                    FastcaseImport.objects.bulk_create(fastcase_imports_to_create)

                # save duplicate cases
                if duplicates_to_create:
                    fastcase_duplicates_to_create = []
                    for case in duplicates_to_create:
                        while isinstance(case['duplicate_of'], dict):
                            target_case = case['duplicate_of']
                            if target_case.get('duplicate_of'):
                                case['duplicate_of'] = target_case['duplicate_of']
                            else:
                                case['duplicate_of'] = target_case['db']
                        fastcase_duplicates_to_create.append(FastcaseImport(duplicate_of=case['duplicate_of'], data=case['orig'], path=case['path'], batch=batch))
                    FastcaseImport.objects.bulk_create(fastcase_duplicates_to_create)

        update_reporter_years(reporter_id=reporter.id)
