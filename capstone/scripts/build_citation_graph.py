""" Extracts, validates, and stores citations from a Case object """

def extract_potential_citations_from_casebody(casebody):
    """ Turns a casebody string into a list of potential citations """
    assert isinstance(casebody, str), 'casebody must be a string'
    citation_graph = []
    # TODO(https://github.com/harvard-lil/capstone/pull/709): Actually extract citations
    return citation_graph
