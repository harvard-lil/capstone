import pytest
from scripts.extract_citations import extract

@pytest.mark.django_db
def test_extract_citation():
    case_text_with_citations = "of the less. State v. Scott, 24 Vt. 127; " \
                          "State v. Thornton, 56 Vt. 35; " \
                          "State v. Albano, 92 Vt. 51, 55, 102 Atl. 333, and cases cited in these cases."
    actual_citations = [
        "24 Vt. 127",
        "56 Vt. 35",
        "92 Vt. 51",
        "102 Atl. 333"
    ]
    case_text_no_citations = "Assault and Battery, § 14.\n" \
                             "In our opinion the true rule is stated by " \
                             "Mr. Bishop in his work on Criminal Law (vol. 2, 8th ed., § 32) in"
    hits, misses = extract(case_text_with_citations)
    assert len(hits.keys()) == 4

    def assert_found_in_case(citation):
        assert citation in hits

    [assert_found_in_case(cite) for cite in actual_citations]

    hits, misses = extract(case_text_no_citations)
    assert len(hits) == 0
