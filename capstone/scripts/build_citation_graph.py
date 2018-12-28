"""
  Extracts, validates, and stores citations from a Case object. Inspired (with permission) by
  https://github.com/freelawproject/courtlistener/blob/master/cl/citations/reporter_tokenizer.py
"""
import re
from enum import Enum, auto, unique

from reporters_db import EDITIONS, VARIATIONS_ONLY

REPORTER_LIST = list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys())
REPORTER_LIST.sort(key=len, reverse=True)
REPORTER_SET = set(REPORTER_LIST)
REPORTER_STR = '|'.join(map(re.escape, REPORTER_LIST))
REPORTER_RE = re.compile("\s(%s)\s" % REPORTER_STR)
SPACING_RE = re.compile("[\s,;:.()[\]{}]+")

@unique
class __CasebodyToken(Enum):
    NOOP = auto()
    NUMBER = auto()
    REPORTER = auto()

def __tokenize_casebody(casebody):
    tokens = []
    reporter_split_tokens = REPORTER_RE.split(casebody)
    for reporter_split_token in reporter_split_tokens:
        if reporter_split_token in REPORTER_SET:
            if reporter_split_token in VARIATIONS_ONLY.keys():
                corrected_reporter = VARIATIONS_ONLY[reporter_split_token][0]
            else:
                corrected_reporter = reporter_split_token
            tokens.append((corrected_reporter, __CasebodyToken.REPORTER))
        else:
            spacing_split_tokens = SPACING_RE.split(reporter_split_token)
            for spacing_split_token in spacing_split_tokens:
                if spacing_split_token.isdigit():
                    tokens.append((spacing_split_token, __CasebodyToken.NUMBER))
                else:
                    tokens.append((spacing_split_token, __CasebodyToken.NOOP))
    return tokens

def extract_potential_citations_from_casebody(casebody):
    """ Turns a casebody string into a list of potential citations """
    assert isinstance(casebody, str), 'casebody must be a string'
    citation_graph = []
    if len(casebody) == 0:
        return citation_graph
    # TODO(https://github.com/harvard-lil/capstone/pull/709): Optimize (too many string operations)
    found_reporters = set(REPORTER_RE.findall(casebody))
    for found_reporter in found_reporters:
        if found_reporter in VARIATIONS_ONLY.keys():
            corrected_reporter = VARIATIONS_ONLY[found_reporter][0]
            corrected_casebody = casebody.replace(found_reporter, corrected_reporter)
        else:
            corrected_reporter = found_reporter
            corrected_casebody = casebody
        corrected_reporter_re = re.compile("([0-9]+\s%s\s[0-9]+)" % corrected_reporter)
        citation_graph += corrected_reporter_re.findall(corrected_casebody)
    # TODO(https://github.com/harvard-lil/capstone/pull/709): Support Id. citation extraction (Id.)
    # TODO(https://github.com/harvard-lil/capstone/pull/709): Support exact page extraction (... at 666)
    # TODO(https://github.com/harvard-lil/capstone/pull/709): Support signal and index extraction (see also ...; cf. ...)
    return citation_graph
