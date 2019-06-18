import json
import lzma
import pytest
from mock import mock

import scripts.ngrams
from capdb.models import NgramWord, NgramObservation, CaseBodyCache


@pytest.mark.django_db
def test_ngrams(file_storage, three_cases, jurisdiction):
    # set up two jurisdictions
    jur0 = jurisdiction
    jur0.slug = 'jur0'
    jur0.save()
    jur1 = three_cases[0].jurisdiction
    jur1.slug = 'jur1'
    jur1.save()

    # set up three cases across two jurisdictions, all in same year
    case_settings = [
        (jur0, '"One? two three." Four!', 2000),
        (jur1, "One 'two three' don't.", 2000),
        (jur1, "(Two, three, don't, don't)", 2000),
    ]
    tokens = {'one', 'two', 'three', 'four', "don't"}
    for case, (jur, text, year) in zip(three_cases, case_settings):
        case.jurisdiction = jur
        case.jurisdiction_slug = jur.slug  # something about the test env is stopping the trigger from setting this
        case.decision_date = case.decision_date.replace(year=year)
        case.save()
        CaseBodyCache(metadata=case, text=text).save()

    # run ngram code
    with mock.patch('scripts.ngrams.ngram_storage', file_storage):
        scripts.ngrams.ngram_jurisdictions()
        scripts.ngrams.merge_jurisdiction_years()
        scripts.ngrams.merge_total()

        # check list of created files
        paths = set(file_storage.iter_files_recursive())
        assert paths == {
            'totals.json',
            'jurisdiction_year/jur0_2000-1.tsv.xz', 'jurisdiction_year/jur0_2000-2.tsv.xz', 'jurisdiction_year/jur0_2000-3.tsv.xz',
            'jurisdiction_year/jur1_2000-1.tsv.xz', 'jurisdiction_year/jur1_2000-2.tsv.xz', 'jurisdiction_year/jur1_2000-3.tsv.xz',
            'year/2000-1.tsv.xz', 'year/2000-2.tsv.xz', 'year/2000-3.tsv.xz',
            'total/total-1.tsv.xz', 'total/total-2.tsv.xz', 'total/total-3.tsv.xz',
        }

        # check totals.json
        totals = json.loads(file_storage.contents('totals.json'))
        assert set(totals.keys()) == paths - {'totals.json'}
        assert totals['jurisdiction_year/jur1_2000-3.tsv.xz'] == {'grams': 4, 'documents': 2}
        assert totals['year/2000-3.tsv.xz'] == {'grams': 6, 'documents': 3}
        assert totals['year/2000-3.tsv.xz'] == {'grams': 6, 'documents': 3}
        assert totals['total/total-3.tsv.xz'] == {'grams': 6, 'documents': 3}

        # check total/total-3.tsv.xz
        file_contents = lzma.decompress(file_storage.contents('total/total-3.tsv.xz', 'rb'))
        assert file_contents == b"gram\tinstances\tdocuments\none two three\t2\t2\nthree don't don't\t1\t1\ntwo three don't\t2\t2\ntwo three four\t1\t1\n", \
            "File contents of total/total-3.tsv.xz no longer match. Found %s" % file_contents

        # run ingest
        scripts.ngrams.ingest_threshold = 1
        scripts.ngrams.load_database()
        assert set(NgramWord.objects.values_list('word', flat=True)) == tokens
        for ngram, jur, year, instance_count, document_count in [
            ["don't", jur1, 2000, 3, 2],
            ["don't", None, 2000, 3, 2],
            ["don't", None, None, 3, 2],
            ["two three", jur1, 2000, 2, 2],
            ["two three", None, 2000, 3, 3],
            ["two three", None, None, 3, 3],
            ["two three don't", jur1, 2000, 2, 2],
            ["two three don't", None, 2000, 2, 2],
            ["two three don't", None, None, 2, 2],
        ]:
            obs = NgramObservation.objects.from_string(ngram).get(jurisdiction=jur, year=year)
            assert obs.instance_count == instance_count
            assert obs.document_count == document_count
