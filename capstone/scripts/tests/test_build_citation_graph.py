""" Tests ../build_citation_graph.py using content from https://supreme.justia.com/cases/federal/us/532/661/ """
import pytest
from scripts import build_citation_graph

@pytest.mark.parametrize("casebody, expected_citations", [
    ("", []),
])
def test_extract_potential_citations_from_casebody(casebody, expected_citations):
    assert extract_potential_citations_from_casebody(casebody) == expected_citations
