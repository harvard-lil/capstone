import pytest
from flaky import flaky

from capapi.views.api_views import NgramViewSet


@flaky(max_runs=10)  # ngrammed_cases call to ngram_jurisdictions doesn't reliably work because it uses multiprocessing within pytest environment
@pytest.mark.django_db
def test_ngrams(request):
    ngrammed_cases = request.getfixturevalue('ngrammed_cases')  # load fixture inside test so flaky() can catch errors
    from capdb.storages import ngram_kv_store_ro  # import here so pytest won't inspect and un-lazy it during test collection

    # check totals
    totals = NgramViewSet.load_totals()
    # keys are (jur.id, year, n), values are [gram count, document count]
    assert totals[(None, None, 3)] == [6, 3]
    assert totals[(None, 2000, 3)] == [6, 3]
    assert totals[(ngrammed_cases[1].jurisdiction_id, 2000, 3)] == [4, 2]

    # check trigram values
    trigrams = {"one two three", "three don't don't", "two three don't", "two three four"}
    stored = {k.decode('utf8')[1:]: v for k, v in ngram_kv_store_ro.get_prefix(b'\3', packed=True)}
    assert trigrams == set(stored.keys())
    assert stored["one two three"] == {None: {None: [2, 2], 100: [2, 2]}, ngrammed_cases[0].jurisdiction_id: [100, 1, 1], ngrammed_cases[1].jurisdiction_id: [100, 1, 1]}

