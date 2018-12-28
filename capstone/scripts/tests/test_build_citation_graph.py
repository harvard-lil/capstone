""" Tests ../build_citation_graph.py using content from https://supreme.justia.com/cases/federal/us/532/661/ """
import pytest
from scripts.build_citation_graph import __CasebodyToken, __tokenize_casebody, extract_potential_citations_from_casebody

@pytest.mark.parametrize("casebody, expected_tokens", [
    (
        "",
        [],
    ),
    (
        "379 U. S. 241",
        [("379", __CasebodyToken.NUMBER), ("U.S.", __CasebodyToken.REPORTER), ("241", __CasebodyToken.NUMBER)],
    ),
    (
        "In Evans v. Laurel Links, Inc.,",
        [("In", __CasebodyToken.NOOP), ("Evans", __CasebodyToken.NOOP), ("v", __CasebodyToken.NOOP), ("Laurel", __CasebodyToken.NOOP), ("Links", __CasebodyToken.REPORTER), ("Inc", __CasebodyToken.NUMBER)],
    ),
])
def test_tokenize_casebody(casebody, expected_tokens):
    assert __tokenize_casebody(casebody) == expected_tokens

@pytest.mark.parametrize("casebody, expected_citations", [
    (
        "",
        [],
    ),
    pytest.param(
        0,
        [],
        marks=pytest.mark.xfail,
    ),
    (
        "379 U. S. 241",
        ["379 U.S. 241"],
    ),
    (
        "In Evans v. Laurel Links, Inc., 261 F. Supp. 474, 477 (ED Va. 1966), a class action brought",
        ["261 F. Supp. 474"],
    ),
    (
        "See, e. g., Birchem v. Knights of Columbus, 116 F.3d 310, 312-313 (CA8 1997); cf. Nationwide Mut. Ins. Co. v. Darden, 503 U. S. 318, 322323 (1992).",
        ["116 F.3d 310", "503 U.S. 318"],
    ),
])
def test_extract_potential_citations_from_casebody(casebody, expected_citations):
    assert extract_potential_citations_from_casebody(casebody) == expected_citations
