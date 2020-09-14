import re
from collections import defaultdict
from datetime import datetime
from string import ascii_lowercase

from capapi.resources import cite_extracting_regex
from capdb.models import ExtractedCitation, normalize_cite


def get_editions(REPORTERS=None):
    """
        Process REPORTERS into a lookup dict from reporter string or normalized reporter string to edition data.

        Given:
        >>> REPORTERS = {
        ...     'Foo': [
        ...         {
        ...             'editions': {
        ...                 'Foo': {"start": datetime(1900, 1, 1), "end": datetime(1910, 1, 1)},
        ...                 'Foo 2d.': {"start": datetime(1910, 1, 1), "end": None},
        ...             },
        ...             'variations': {
        ...                 'foo': 'Foo',
        ...                 'Food': 'Foo',
        ...             }
        ...         },
        ...         {
        ...             'editions': {
        ...                 'Foo': {"start": datetime(1800, 1, 1), "end": datetime(1810, 1, 1)},
        ...             },
        ...             'variations': {
        ...                 'foo': 'Foo',
        ...                 'Fool': 'Foo',
        ...             }
        ...         },
        ...     ]
        ... }

        Each reporter string maps to its possible resolutions, sorted in reverse-end-date order:
        >>> editions = get_editions(REPORTERS)
        >>> foo1 = {'reporter': 'Foo', 'start_year': 1900, 'end': datetime(1910, 1, 1)}
        >>> foo2d = {'reporter': 'Foo 2d.', 'start_year': 1910, 'end': datetime(9999, 1, 1)}
        >>> foo2 = {'reporter': 'Foo', 'start_year': 1800, 'end': datetime(1810, 1, 1)}
        >>> assert editions == {
        ...     'Foo': [foo1, foo2],
        ...     'foo': [foo1, foo2],
        ...     'Foo 2d.': [foo2d],
        ...     'foo2d': [foo2d],
        ...     'Food': [foo1],
        ...     'food': [foo1],
        ...     'Fool': [foo2],
        ...     'fool': [foo2],
        ... }
    """
    if REPORTERS is None:
        from reporters_db import REPORTERS
    editions = defaultdict(list)
    not_ended_date = datetime(9999, 1, 1)
    unknown_start_date = datetime(1750, 1, 1)

    def append(k, v):
        for key in (k, normalize_cite(k)):
            if v not in editions[key]:
                editions[key].append(v)

    for reporter_cluster in REPORTERS.values():
        for reporter in reporter_cluster:
            local_editions = {}
            for k, v in reporter["editions"].items():
                local_editions[k] = edition = {
                    'reporter': k,
                    'start_year': 0 if v['start'] == unknown_start_date else v['start'].year,
                    'end': v['end'] or not_ended_date,
                }
                append(k, edition)
            for k, v in reporter["variations"].items():
                append(k, local_editions[v])

    # sort candidates for each string: first prefer exact matches, then editions that ended more recently
    for edition_key, candidates in editions.items():
        candidates.sort(reverse=True, key=lambda c: (c['reporter'] == edition_key, c['end']))

    return editions


# set up reporter lookup tables
EDITIONS = get_editions()
INVALID_REPORTERS = set(ascii_lowercase) | {'at', 'or', 'p.', 'c.', 'B'}
TRANSLATIONS = {'la.': 'Ia.', 'Yt.': 'Vt.', 'Pae.': 'Pac.'}


def extract_citations_from_text(text, max_year=9999, misses=None):
    # use dict.fromkeys to remove dupes while preserving order
    for match in dict.fromkeys(re.findall(cite_extracting_regex, text)):
        vol_num, reporter_str, page_num = match

        # fix known OCR errors
        if reporter_str in TRANSLATIONS:
            reporter_str = TRANSLATIONS[reporter_str]

        # skip strings like 'or' that are known non-citations
        if reporter_str in INVALID_REPORTERS:
            if misses is not None:
                misses['blocked'][reporter_str] += 1
            continue

        # Look for found reporter string in the official and nominative REPORTER dicts
        # Try exact match, then normalized match
        candidates = EDITIONS.get(reporter_str) or EDITIONS.get(normalize_cite(reporter_str))
        if not candidates:
            # reporter not found, removing cite and adding to misses list
            if misses is not None:
                misses['not_found'][reporter_str] += 1
            continue

        # Find a candidate reporter that was in operation prior to this case being published.
        # Reporters are sorted by end date, so this will prefer newer reporters.
        best_candidate = next((c for c in candidates if c['start_year'] <= max_year), None)
        if not best_candidate:
            if misses is not None:
                misses['invalid_date'][reporter_str] += 1
            continue

        cite = " ".join(match)
        normalized_cite = "%s %s %s" % (vol_num, best_candidate['reporter'], page_num)

        yield cite, normalized_cite, vol_num, reporter_str, page_num


def extract_citations(case):
    misses = defaultdict(lambda: defaultdict(int))
    case_citations = [
        ExtractedCitation(
            cite=cite,
            normalized_cite=normalize_cite(normalized_cite),
            cited_by=case,
            reporter_name_original=reporter_str,
            volume_number_original=vol_num,
            page_number_original=page_num)
        for cite, normalized_cite, vol_num, reporter_str, page_num in
        extract_citations_from_text(case.body_cache.text, case.decision_date.year, misses)
    ]
    return case_citations, misses
