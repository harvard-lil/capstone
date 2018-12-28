"""
  Extracts, validates, and stores citations from a Case object. Inspired (with permission) by
  https://github.com/freelawproject/courtlistener/blob/master/cl/citations/reporter_tokenizer.py
"""
import re
from enum import Enum, unique

from reporters_db import EDITIONS, VARIATIONS_ONLY

REPORTER_LIST = list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys())
REPORTER_LIST.sort(key=len, reverse=True)
REPORTER_SET = set(REPORTER_LIST)
REPORTER_STR = '|'.join(map(re.escape, REPORTER_LIST))
REPORTER_RE = re.compile("\s(%s)\s" % REPORTER_STR)
SPACING_RE = re.compile("[\s,;:.()[\]{}]+")

@unique
class __CasebodyToken(Enum):
    ID = 0 # `Id` style citation
    NOOP = 1 # Token used only to break up patterns
    NUMBER = 2 # [0-9]+
    REPORTER = 3 # Can be found in `REPORTER_SET`

def __tokenize_casebody(casebody):
    """Splits casebody into components and pairs them with `CasebodyToken`s"""
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
                elif spacing_split_token == "":
                    continue
                elif spacing_split_token.lower() == "id":
                    tokens.append(("Id", __CasebodyToken.ID))
                else:
                    tokens.append((spacing_split_token, __CasebodyToken.NOOP))
    return tokens

def __find_citations_in_tokens(tokens):
    """Finds citations within tokens returned by `__tokenize_casebody`"""
    # TODO(https://github.com/harvard-lil/capstone/pull/709): Support exact page extraction (... at 666)
    # TODO(https://github.com/harvard-lil/capstone/pull/709): Support signal and index extraction (see also ...; cf. ...)
    citations = []
    idx = 0
    while idx < len(tokens):
        token_a = tokens[idx]
        idx += 1
        if token_a[1] == __CasebodyToken.ID:
            citations.append(token_a[0])
            continue
        if token_a[1] != __CasebodyToken.NUMBER:
            continue
        if idx == len(tokens):
            break
        token_b = tokens[idx]
        if token_b[1] != __CasebodyToken.REPORTER:
            continue
        idx += 1
        if idx == len(tokens):
            break
        token_c = tokens[idx]
        if token_c[1] != __CasebodyToken.NUMBER:
            continue
        idx += 1
        citations.append(" ".join([token_a[0], token_b[0], token_c[0]]))
    return citations

def extract_potential_citations_from_casebody(casebody):
    """Extracts an ordered list of potential citations from the casebody"""
    assert isinstance(casebody, str), 'casebody must be a string'
    tokens = __tokenize_casebody(casebody)
    return __find_citations_in_tokens(tokens)
