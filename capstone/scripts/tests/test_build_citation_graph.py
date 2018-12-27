""" Tests ../build_citation_graph.py using content from https://supreme.justia.com/cases/federal/us/532/661/ """
import pytest
from scripts import build_citation_graph

@pytest.mark.parametrize("casebody, expected_citations", [
    ("", []),
    pytest.param(0, [], marks=pytest.mark.xfail),
    ("379 U. S. 241", ["379 U. S. 241"]),
    ("In Evans v. Laurel Links, Inc., 261 F. Supp. 474, 477 (ED Va. 1966), a class action brought", ["261 F. Supp. 474"]),
])
def test_extract_potential_citations_from_casebody(casebody, expected_citations):
    actual_citations = build_citation_graph.extract_potential_citations_from_casebody(casebody)
    assert len(actual_citations) == len(expected_citations)
    for idx, _ in enumerate(actual_citations):
        assert actual_citations[idx] == expected_citations[idx]
