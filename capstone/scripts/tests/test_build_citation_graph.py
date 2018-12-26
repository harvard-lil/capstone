""" Tests ../build_citation_graph.py using content from https://supreme.justia.com/cases/federal/us/532/661/ """
import pytest
from scripts import build_citation_graph

@pytest.mark.parametrize("casebody, expected_citations", [
    ("", []),
    pytest.param(0, [], marks=pytest.mark.xfail),
    ("379 U.S. 241", ["379 U.S. 241"])
])
def test_extract_potential_citations_from_casebody(casebody, expected_citations):
    assert build_citation_graph.extract_potential_citations_from_casebody(casebody) == expected_citations
