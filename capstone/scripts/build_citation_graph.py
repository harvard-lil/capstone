"""
  Extracts, validates, and stores citations from a Case object. Inspired (with permission) by
  https://github.com/freelawproject/courtlistener/blob/master/cl/citations/reporter_tokenizer.py
"""
import re

from reporters_db import EDITIONS, VARIATIONS_ONLY

REGEX_LIST = list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys())
REGEX_LIST.sort(key=len, reverse=True)
REGEX_STR = '|'.join(map(re.escape, REGEX_LIST))
REPORTER_RE = re.compile("[0-9]*\s(%s)[0-9]*\s" % REGEX_STR)

def extract_potential_citations_from_casebody(casebody):
    """ Turns a casebody string into a list of potential citations """
    assert isinstance(casebody, str), 'casebody must be a string'
    citation_graph = []
    if len(casebody) == 0:
        return citation_graph
    citation_graph.append(casebody)
    return REPORTER_RE.findall(casebody)
