import re
from string import ascii_lowercase

from reporters_db import EDITIONS, VARIATIONS_ONLY

from capapi.resources import cite_extracting_regex
from capdb.models import ExtractedCitation, normalize_cite


extra_reporters = {'wl'}
valid_reporters = {normalize_cite(c) for c in list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys())} | extra_reporters
invalid_reporters = set(ascii_lowercase) | {'at', 'or', 'p.', 'c.', 'B'}
translations = {'la.': 'Ia.', 'Yt.': 'Vt.', 'Pae.': 'Pac.'}


def extract_citations(case):
    misses = []
    case_citations = []
    for match in set(re.findall(cite_extracting_regex, case.body_cache.text)):
        vol_num, reporter_str, page_num = match

        # fix known OCR errors
        if reporter_str in translations:
            reporter_str = translations[reporter_str]

        # skip strings like 'or' that are known non-citations
        if reporter_str in invalid_reporters:
            misses.append(reporter_str)
            continue

        # Look for found reporter string in the official and nominative REPORTER dicts
        if normalize_cite(reporter_str) not in valid_reporters:
            # reporter not found, removing cite and adding to misses list
            misses.append(reporter_str)
            continue

        cite = " ".join(match)
        case_citations.append(ExtractedCitation(
            cite=cite,
            normalized_cite=normalize_cite(cite),
            cited_by=case,
            reporter_name_original=reporter_str,
            volume_number_original=vol_num,
            page_number_original=page_num))

    return case_citations, misses
