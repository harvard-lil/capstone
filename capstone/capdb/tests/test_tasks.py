import lzma
from pathlib import Path
import pytest
import bagit
import zipfile
import os
import csv
import gzip
import json
from datetime import datetime, date
from reporters_db import EDITIONS, VARIATIONS_ONLY

from django.core.files.storage import FileSystemStorage
from django.db import connections, utils

from capapi.documents import CaseReaderDocument
from capdb.models import CaseMetadata, Court, Reporter, Citation, ExtractedCitation, CaseBodyCache, normalize_cite
from capdb.tasks import get_case_count_for_jur, get_court_count_for_jur, \
    get_reporter_count_for_jur, update_elasticsearch_for_vol, sync_case_body_cache_for_vol, \
    update_elasticsearch_from_queue, run_text_analysis_for_vol

import fabfile
from test_data.test_fixtures.helpers import get_timestamp, check_timestamps_changed, check_timestamps_unchanged


@pytest.mark.django_db
def test_export_cases(case_factory, tmp_path, django_assert_num_queries, elasticsearch, monkeypatch):
    version = date.today().strftime('%Y%m%d')
    case1 = case_factory(jurisdiction__slug="aaa", volume__reporter__short_name="aaa", jurisdiction__whitelisted=False)
    case2 = case_factory(jurisdiction__slug="bbb", volume__reporter__short_name="bbb", jurisdiction__whitelisted=True)
    monkeypatch.setattr("scripts.export.download_files_storage", FileSystemStorage(location=str(tmp_path)))
    changelog = "changelogtext"
    fabfile.export_cases(changelog)
    written_files = sorted(str(i.relative_to(tmp_path)) for i in tmp_path.rglob('*'))
    expected_files = [i.strip() for i in """
        bulk_exports
        bulk_exports/{version}
        bulk_exports/{version}/README.md
        bulk_exports/{version}/by_jurisdiction
        bulk_exports/{version}/by_jurisdiction/README.md
        bulk_exports/{version}/by_jurisdiction/case_metadata
        bulk_exports/{version}/by_jurisdiction/case_metadata/README.md
        bulk_exports/{version}/by_jurisdiction/case_metadata/{case1.jurisdiction.slug}
        bulk_exports/{version}/by_jurisdiction/case_metadata/{case1.jurisdiction.slug}/{case1.jurisdiction.slug}_metadata_{version}.zip
        bulk_exports/{version}/by_jurisdiction/case_metadata/{case2.jurisdiction.slug}
        bulk_exports/{version}/by_jurisdiction/case_metadata/{case2.jurisdiction.slug}/{case2.jurisdiction.slug}_metadata_{version}.zip
        bulk_exports/{version}/by_jurisdiction/case_text_open
        bulk_exports/{version}/by_jurisdiction/case_text_open/README.md
        bulk_exports/{version}/by_jurisdiction/case_text_open/{case2.jurisdiction.slug}
        bulk_exports/{version}/by_jurisdiction/case_text_open/{case2.jurisdiction.slug}/{case2.jurisdiction.slug}_text_{version}.zip
        bulk_exports/{version}/by_jurisdiction/case_text_open/{case2.jurisdiction.slug}/{case2.jurisdiction.slug}_xml_{version}.zip
        bulk_exports/{version}/by_jurisdiction/case_text_restricted
        bulk_exports/{version}/by_jurisdiction/case_text_restricted/README.md
        bulk_exports/{version}/by_jurisdiction/case_text_restricted/{case1.jurisdiction.slug}
        bulk_exports/{version}/by_jurisdiction/case_text_restricted/{case1.jurisdiction.slug}/{case1.jurisdiction.slug}_text_{version}.zip
        bulk_exports/{version}/by_jurisdiction/case_text_restricted/{case1.jurisdiction.slug}/{case1.jurisdiction.slug}_xml_{version}.zip
        bulk_exports/{version}/by_reporter
        bulk_exports/{version}/by_reporter/README.md
        bulk_exports/{version}/by_reporter/case_metadata
        bulk_exports/{version}/by_reporter/case_metadata/README.md
        bulk_exports/{version}/by_reporter/case_metadata/{case1.reporter.short_name_slug}
        bulk_exports/{version}/by_reporter/case_metadata/{case1.reporter.short_name_slug}/{case1.reporter.short_name_slug}_metadata_{version}.zip
        bulk_exports/{version}/by_reporter/case_metadata/{case2.reporter.short_name_slug}
        bulk_exports/{version}/by_reporter/case_metadata/{case2.reporter.short_name_slug}/{case2.reporter.short_name_slug}_metadata_{version}.zip
        bulk_exports/{version}/by_reporter/case_text_open
        bulk_exports/{version}/by_reporter/case_text_open/README.md
        bulk_exports/{version}/by_reporter/case_text_open/{case2.reporter.short_name_slug}
        bulk_exports/{version}/by_reporter/case_text_open/{case2.reporter.short_name_slug}/{case2.reporter.short_name_slug}_text_{version}.zip
        bulk_exports/{version}/by_reporter/case_text_open/{case2.reporter.short_name_slug}/{case2.reporter.short_name_slug}_xml_{version}.zip
        bulk_exports/{version}/by_reporter/case_text_restricted
        bulk_exports/{version}/by_reporter/case_text_restricted/README.md
        bulk_exports/{version}/by_reporter/case_text_restricted/{case1.reporter.short_name_slug}
        bulk_exports/{version}/by_reporter/case_text_restricted/{case1.reporter.short_name_slug}/{case1.reporter.short_name_slug}_text_{version}.zip
        bulk_exports/{version}/by_reporter/case_text_restricted/{case1.reporter.short_name_slug}/{case1.reporter.short_name_slug}_xml_{version}.zip
    """.strip().format(case1=case1, case2=case2, version=version).splitlines()]

    assert expected_files == written_files
    assert changelog in (tmp_path / 'bulk_exports' / version / 'README.md').read_text()

    for export_path in tmp_path.rglob('*.zip'):
        bag_path = export_path.stem
        export_path = str(export_path)
        case = case1 if case1.jurisdiction.slug in export_path or case1.reporter.short_name_slug in export_path else case2

        # check bag format
        with zipfile.ZipFile(export_path) as zf:
            zf.extractall(str(tmp_path))
        bag = bagit.Bag(str(tmp_path / bag_path))
        bag.validate()

        # check data file
        with lzma.open(str(tmp_path / bag_path / 'data' / 'data.jsonl.xz')) as in_file:
            records = [json.loads(str(line, 'utf8')) for line in in_file if line]
        assert len(records) == 1
        assert records[0]['name'] == case.name
        if 'xml' in export_path:
            assert records[0]['casebody']['data'].startswith('<?xml')
        elif 'text' in export_path:
            assert 'opinions' in records[0]['casebody']['data']
        else:
            assert 'casebody' not in records[0]


@pytest.mark.django_db
def test_write_inventory_files(tmpdir):
    # write inventory files to a temporary directory
    td = str(tmpdir)
    fabfile.write_inventory_files(output_directory=td)
    # gunzip them and read them in
    contents = ""
    for base in ["1", "2"]:
        file_path = '%s/%s.csv.gz' % (td, base)
        assert os.path.exists(file_path)
        with gzip.open(file_path, 'rt') as f:
            contents += f.read()
    # check the contents
    assert 'harvard-ftl-shared' in contents
    for dir_name, subdir_list, file_list in os.walk('test_data/from_vendor'):
        for file_path in file_list:
            if file_path == '.DS_Store':
                continue
            file_path = os.path.join(dir_name, file_path)
            assert file_path[len('test_data/'):] in contents


@pytest.mark.django_db
def test_show_slow_queries(capsys):
    cursor = connections['capdb'].cursor()
    try:
        cursor.execute("create extension if not exists pg_stat_statements;")
        fabfile.show_slow_queries()
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "slow query report" in output['text']
    except utils.OperationalError:
        pytest.skip("pg_stat_statements is not in shared_preload_libraries")


@pytest.mark.django_db
def test_get_court_count_for_jur(court, jurisdiction):
    court.jurisdiction = jurisdiction
    court.save()

    results = get_court_count_for_jur(jurisdiction.id)
    assert results['total'] == Court.objects.filter(jurisdiction=jurisdiction).count()
    date = datetime.strptime(results['recorded'], "%Y-%m-%d %H:%M:%S.%f")
    assert date.day == datetime.now().day


@pytest.mark.django_db
def test_get_case_count_for_jur(three_cases, jurisdiction):
    for case in three_cases:
        case.jurisdiction = jurisdiction
        case.save()

    results = get_case_count_for_jur(jurisdiction.id)

    for case in three_cases:
        assert case.decision_date.year in results['years']

    date = datetime.strptime(results['recorded'], "%Y-%m-%d %H:%M:%S.%f")
    assert date.day == datetime.now().day
    assert results['total'] == CaseMetadata.objects.filter(jurisdiction=jurisdiction.id).count()


@pytest.mark.django_db
def test_get_reporter_count_for_jur(reporter, jurisdiction):
    reporter.jurisdictions.add(jurisdiction)
    reporter.full_name = 'Alabama Reports'
    reporter.save()

    oldest_reporter = Reporter.objects.filter(jurisdictions=jurisdiction).order_by('start_year').first()
    reporter.start_year = oldest_reporter.start_year - 1
    reporter.save()

    results = get_reporter_count_for_jur(jurisdiction.id)

    assert results['firsts']['name'] == reporter.full_name
    assert results['firsts']['id'] == reporter.id

    date = datetime.strptime(results['recorded'], "%Y-%m-%d %H:%M:%S.%f")
    assert date.day == datetime.now().day
    assert results['total'] == Reporter.objects.filter(jurisdictions=jurisdiction.id).count()


@pytest.mark.django_db
def test_update_case_frontend_url(case_factory):
    case_metadata = case_factory(citations__cite="123 Test 456", volume__volume_number="123", citations__type="official")
    citation = case_metadata.citations.first()
    citation.cite = "123 Test 456"
    citation.type = "official"
    citation.save()
    Citation(cite="456 Test2 789", type="parallel", case=case_metadata).save()
    fabfile.update_case_frontend_url(update_existing=True)
    case_metadata.refresh_from_db()
    assert case_metadata.frontend_url == "/test/123/456/"


@pytest.mark.django_db
def test_update_case_frontend_url_hyphen_cite(case):
    case.volume.volume_number = "123"
    case.volume.save()

    citation = case.citations.first()
    citation.cite = "123-Test-456"
    citation.save()
    fabfile.update_case_frontend_url(update_existing=True)
    case.refresh_from_db()
    assert case.frontend_url == "/test/123/456/%s/" % citation.case_id


@pytest.mark.django_db
def test_update_case_frontend_url_bad_cite(case):
    citation = case.citations.first()
    citation.cite = "BAD"
    citation.save()
    fabfile.update_case_frontend_url(update_existing=True)
    case.refresh_from_db()
    assert case.frontend_url == "/%s/%s/%s/%s/" % (case.reporter.short_name_slug, case.volume.volume_number, case.first_page, citation.case_id)


@pytest.mark.django_db
def test_redact_id_numbers(case_factory):
    # redact some numbers
    case = case_factory(body_cache__text="text 123-45-6789  # normal SSN")
    fabfile.redact_id_numbers()
    case.refresh_from_db()
    assert case.no_index_redacted == {'123-45-6789': 'XXX-XX-XXXX'}

    # test updating existing no_index_redacted
    case.no_index_redacted['foo'] = 'bar'
    case.save()
    case.body_cache.text += "more text 123 — 45 — 6789  # mdashes and whitespace "
    case.body_cache.save()
    fabfile.redact_id_numbers()
    case.refresh_from_db()
    assert case.no_index_redacted == {'123 — 45 — 6789': 'XXX — XX — XXXX', '123-45-6789': 'XXX-XX-XXXX', 'foo': 'bar'}

    # test A-numbers
    case.no_index_redacted = {}
    case.save()
    case.body_cache.text="""
        A12345678  # 8 digit A-number
        A123456789  # 9 digit A-number
        A-12345678  # 8 digit A-number with hyphen
        A — 123456789  # 9 digit A-number with mdash and spaces
        A — 1 -2- 3 45-67  8--9  # just why
    """
    case.body_cache.save()
    fabfile.redact_id_numbers()
    case.refresh_from_db()
    assert case.no_index_redacted == {
        'A12345678': 'AXXXXXXXX',
        'A — 123456789': 'A — XXXXXXXXX',
        'A123456789': 'AXXXXXXXXX',
        'A-12345678': 'A-XXXXXXXX',
        'A — 1 -2- 3 45-67  8--9': 'A — X -X- X XX-XX  X--X',
    }


@pytest.mark.django_db
def test_extract_citations(case_factory, tmpdir, settings, elasticsearch):
    from scripts.extract_cites import EDITIONS as processed_editions
    settings.MISSED_CITATIONS_DIR = str(tmpdir)
    blocked_by_date = set(k for k in list(EDITIONS.keys()) + list(VARIATIONS_ONLY.keys()) if all(c['start_year']>2000 for c in processed_editions[k]))
    legitimate_cites = [
        "225 F. Supp. 552",                         # correct
        ["125 f supp 152", "125 F. Supp. 152"],     # normalized
        ["125 Burnett (Wis.) 152", "125 Bur. 152"], # normalized
        ["1 F. 2d 2", "1 F.2d 2"],                  # not matched as "1 F. 2"
        "2 1/2 Mass. 1",                            # special volume numbers
        "3 Suppl. Mass. 2",                         # special volume numbers
        "1 La.App. 5 Cir. 2",                       # not matched as "1 La.App. 5"
        "2000 WL 12345",                            # vendor cite
    ]
    legitimate_cites += ["1 %s 1" % c for c in EDITIONS.keys() if c not in blocked_by_date]
    legitimate_cites += [["1 %s 1" % k, "1 %s 1" % v] for k, vv in VARIATIONS_ONLY.items() for v in vv if k not in blocked_by_date]
    legitimate_cites_normalized = set(normalize_cite(c if type(c) is str else c[1]) for c in legitimate_cites)
    legitimate_cites = [c if type(c) is str else c[0] for c in legitimate_cites]
    illegitimate_cites = [
        "2 Dogs 3",             # unrecognized reporter
        "3 Dogs 4",             # duplicate unrecognized reporter
        "1 or 2",               # not matched as 1 Or. 2
        "word1 Mass. 2word",    # not matched if part of larger word
        "1 Mass.\n 2",          # no match across newlines
        "1 A.3d 1",             # no match to reporter that started publishing in 2010
    ]
    illegitimate_cites += ["1 %s 1" % c for c in blocked_by_date]
    case = case_factory(body_cache__text=", some text, ".join(legitimate_cites+illegitimate_cites), decision_date=datetime(2000, 1, 1))
    fabfile.extract_all_citations()
    update_elasticsearch_from_queue()

    # check extracted cites
    cites = list(ExtractedCitation.objects.all())
    cite_set = set(c.cite for c in cites)
    normalized_cite_set = set(c.normalized_cite for c in cites)
    assert cite_set == set(legitimate_cites)
    assert normalized_cite_set == legitimate_cites_normalized
    assert all(c.cited_by_id == case.pk for c in cites)
    assert set(c['cite'] for c in CaseReaderDocument.get(id=case.pk).extractedcitations) == cite_set
    assert set(c['normalized_cite'] for c in CaseReaderDocument.get(id=case.pk).extractedcitations) == normalized_cite_set

    # remove a cite and add a cite --
    # make sure IDs of unchanged cites are still the same
    removed_cite_str = legitimate_cites[0]
    added_cite_str = '123 F. Supp. 456'
    case.body_cache.text = case.body_cache.text.replace(removed_cite_str, '') + ', some text, ' + added_cite_str
    case.body_cache.save()
    fabfile.extract_all_citations()
    new_cites = list(ExtractedCitation.objects.all())
    removed_cite = next(c for c in cites if c.cite == removed_cite_str)
    added_cite = next(c for c in new_cites if c.cite == added_cite_str)
    assert {(c.id, c.cite) for c in new_cites} == ({(c.id, c.cite) for c in cites} | {(added_cite.id, added_cite.cite)}) - {(removed_cite.id, removed_cite.cite)}

    # check missed_citations files
    misses = json.loads(Path(settings.MISSED_CITATIONS_DIR, "missed_citations-%s.json" % case.volume_id).read_text())[str(case.id)]
    assert misses["not_found"] == {"Dogs": 2}
    assert misses["blocked"] == {"or": 1}
    assert misses["invalid_date"] == {k: 1 for k in blocked_by_date | {"A.3d"}}


@pytest.mark.django_db
def test_update_elasticsearch_for_vol(three_cases, volume_metadata, django_assert_num_queries, elasticsearch):
    with django_assert_num_queries(select=2, update=1):
        update_elasticsearch_for_vol(volume_metadata.barcode)


@pytest.mark.django_db
def test_sync_case_body_cache_for_vol(volume_metadata, case_factory, django_assert_num_queries, elasticsearch):
    cases = [case_factory(volume=volume_metadata) for c in range(3)]

    # full sync
    CaseBodyCache.objects.update(text='blank')
    with django_assert_num_queries(select=5, update=2, insert=1):
        sync_case_body_cache_for_vol(volume_metadata.barcode)
    assert all(c.text == 'Case text 0\nCase text 1Case text 2\nCase text 3\n' for c in CaseBodyCache.objects.all())

    # check analysis
    expected_analysis = [
        ('cardinality', 6),
        ('char_count', 47),
        ('ocr_confidence', 1.0),
        ('sha256', 'da95df9d6d5d506285c9a8f9010560fa57905f64b3e94748b8854d678e18f0cc'),
        ('simhash', '1:6e45862a08eb1d4c'),
        ('word_count', 11)
    ]
    for case in cases:
        assert sorted((a.key, a.value) for a in case.analysis.all()) == expected_analysis

    # text/json sync
    CaseBodyCache.objects.update(text='blank')
    with django_assert_num_queries(select=3, update=2, insert=1):
        sync_case_body_cache_for_vol(volume_metadata.barcode, rerender=False)
    assert all(c.text == 'Case text 0\nCase text 1Case text 2\nCase text 3\n' for c in CaseBodyCache.objects.all())


@pytest.mark.django_db
def test_run_text_analysis(transactional_db, reset_sequences, case):
    timestamp = get_timestamp(case)

    # can update text analysis
    run_text_analysis_for_vol(case.volume_id)
    timestamp = check_timestamps_changed(case, timestamp)
    expected_analysis = [
        ('cardinality', 3),
        ('char_count', 11),
        ('ocr_confidence', 1.0),
        ('sha256', 'c66397f6ebb7b7e5dfd7191e81ee17db2d8c92bcb45f0c41b1e1c5307334622e'),
        ('simhash', '1:025d04b98eb62906'),
        ('word_count', 3)
    ]
    assert sorted((a.key, a.value) for a in case.analysis.all()) == expected_analysis

    # if text analysis fields unchanged, last_updated is unchanged
    run_text_analysis_for_vol(case.volume_id)
    check_timestamps_unchanged(case, timestamp)
    assert sorted((a.key, a.value) for a in case.analysis.all()) == expected_analysis


@pytest.mark.django_db
def test_export_citation_graph(case_factory, tmpdir, elasticsearch, extracted_citation_factory, citation_factory, jurisdiction_factory):
    output_folder = Path(str(tmpdir))
    (
        cite_from, cite_to, different_jur_cite, cite_to_aka, another_cite_to,
        cite_not_in_cap, duplicate_cite, future_cite
    ) = ["%s Cite %s" % (i, i) for i in range(1, 9)]

    jur1, jur2, jur3 = [jurisdiction_factory() for _ in range(3)]

    # source case
    case_from = case_factory(citations__cite=cite_from, decision_date=datetime(2000, 1, 1), jurisdiction=jur1)
    extracted_citation_factory(cite=cite_from, cited_by_id=case_from.id)  # cite to self is ignored

    # dest case should appear
    case_to = case_factory(citations__cite=cite_to, decision_date=datetime(1990, 1, 1), jurisdiction=jur1)
    extracted_citation_factory(cite=cite_to, cited_by_id=case_from.id)
    citation_factory(cite=cite_to_aka, case=case_to)
    extracted_citation_factory(cite=cite_to_aka, cited_by_id=case_from.id)  # we should only include this parallel cite once

    # different jur source case
    different_jur_case = case_factory(citations__cite=different_jur_cite, decision_date=datetime(2000, 1, 1), jurisdiction=jur2)
    extracted_citation_factory(cite=cite_to, cited_by_id=different_jur_case.id)

    # second dest case should appear
    another_case_to = case_factory(citations__cite=another_cite_to, decision_date=datetime(1990, 1, 1), jurisdiction=jur3)
    extracted_citation_factory(cite=another_cite_to, cited_by_id=case_from.id)

    # multiple cases with same cite should be filtered out
    [case_factory(citations__cite=duplicate_cite, jurisdiction=jur1) for _ in range(3)]
    extracted_citation_factory(cite=duplicate_cite, cited_by_id=case_from.id)

    # cites matching zero cases should be filtered out
    extracted_citation_factory(cite=cite_not_in_cap, cited_by_id=case_from.id)

    # citations to future cases should be filtered out
    case_factory(citations__cite=future_cite, decision_date=datetime(2010, 1, 1), jurisdiction=jur1)
    extracted_citation_factory(cite=future_cite, cited_by_id=case_from.id)

    # perform export
    fabfile.export_citation_graph(output_folder=str(output_folder))

    # check citations.csv.gz
    with gzip.open(str(output_folder / "citations.csv.gz"), 'rt') as f:
        results = list(csv.reader(f))
    assert len(results) == 2
    assert results[0][0] == str(case_from.id)
    assert set(results[0][1:]) == {str(case_to.id), str(another_case_to.id)}
    assert results[1][0] == str(different_jur_case.id)
    assert set(results[1][1:]) == {str(case_to.id)}

    # check README.md
    results = output_folder.joinpath("README.md").read_text()
    assert results.endswith("\n* Nodes: 4\n* Edges: 3\n")

    # check metadata.csv.gz
    with gzip.open(str(output_folder / "metadata.csv.gz"), 'rt') as f:
        results = list(csv.DictReader(f))
    assert set(int(r['id']) for r in results) == {case_from.id, case_to.id, another_case_to.id, different_jur_case.id}
    for r in results:  # check 'cites' column
        assert set(c.cite for c in Citation.objects.filter(case_id=r['id'])) == set(r['cites'].split('; '))

    # check per-jurisdiction citations.csv.gz
    jur_folder = output_folder / "by_jurisdiction" / jur1.name
    with gzip.open(str(jur_folder / "citations.csv.gz"), 'rt') as f:
        results = list(csv.reader(f))
    assert len(results) == 1
    assert results[0][0] == str(case_from.id)
    assert set(results[0][1:]) == {str(case_to.id)}

    # check README.md
    results = jur_folder.joinpath("README.md").read_text()
    assert results.endswith("\n* Nodes: 2\n* Edges: 1\n")

    # check metadata.csv.gz
    with gzip.open(str(jur_folder / "metadata.csv.gz"), 'rt') as f:
        results = list(csv.DictReader(f))
    assert set(int(r['id']) for r in results) == {case_from.id, case_to.id}
    for r in results:  # check 'cites' column
        assert set(c.cite for c in Citation.objects.filter(case_id=r['id'])) == set(r['cites'].split('; '))


@pytest.mark.django_db(transaction=True)
def test_pagerank(tmp_path, reset_sequences, three_cases):
    """ Test calculate_pagerank_scores and load_pagerank_scores """
    citations_file = tmp_path / 'citations.csv.gz'
    pagerank_file = tmp_path / 'pagerank.csv.gz'
    with gzip.open(citations_file, 'wt') as f:
        f.write("%s,%s,%s\n%s,%s\n" % (three_cases[0].id, three_cases[0].id, three_cases[2].id, three_cases[1].id, three_cases[2].id))
    fabfile.calculate_pagerank_scores(citations_file, pagerank_file)
    fabfile.load_pagerank_scores(pagerank_file)
    with gzip.open(pagerank_file, 'rt') as f:
        reader = csv.reader(f)
        headers = next(reader)
        pageranks = {int(row[0]): [float(row[1]), float(row[2])] for row in reader}
    for case in three_cases:
        assert case.analysis.get(key='pagerank').value == {
            'raw': pageranks[case.id][0],
            'percentile': pageranks[case.id][1],
        }

    # check updating pagerank
    timestamps = [get_timestamp(c) for c in three_cases]
    pageranks[three_cases[0].id][0] *= 0.9
    with gzip.open(pagerank_file, 'wt') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows([k]+v for k, v in pageranks.items())
    fabfile.load_pagerank_scores(pagerank_file)
    check_timestamps_changed(three_cases[0], timestamps[0])
    assert three_cases[0].analysis.get(key='pagerank').value['raw'] == pageranks[three_cases[0].id][0]
    check_timestamps_unchanged(three_cases[1], timestamps[1])
    check_timestamps_unchanged(three_cases[2], timestamps[2])
