from elasticsearch.exceptions import RequestError
import pytest

from capapi.documents import CaseDocument
from capapi.resources import parallel_execute


@pytest.mark.django_db(databases=['capdb'])
def test_parallel_execute(three_cases, elasticsearch):
    # run search in parallel
    expected_ids = [str(three_cases[0].id), str(three_cases[1].id)]
    results = parallel_execute(CaseDocument.search().filter('terms', id=expected_ids), desired_docs=3)
    assert sorted(results) == expected_ids

    # errors are raised
    with pytest.raises(RequestError):
        parallel_execute(CaseDocument.search().sort('invalid'), desired_docs=1)
