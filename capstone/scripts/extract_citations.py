import re
from reporters_db import REPORTERS, VARIATIONS_ONLY


def extract(case_text):
    results = re.finditer(r"\d+\s+\w+(\.?\s?\w?\'?)*\.*\s?\d+\w?\s?\d+", case_text)
    possible_citations = []
    for result in results:
        citation = result.group()
        parts = citation.split(" ")
        # citation: volume number, reporter short name, page number
        rep_short_name = " ".join(parts[1:-1])
        if rep_short_name in REPORTERS or rep_short_name in VARIATIONS_ONLY:
            # check if exists as official or variation name
            possible_citations.append(citation)

    return possible_citations

