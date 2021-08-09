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

from django.core.files.storage import FileSystemStorage
from django.db import connections, utils
from elasticsearch import NotFoundError

from capapi import api_reverse
from capapi.documents import CaseDocument
from capdb.models import CaseMetadata, Court, Reporter, Citation, ExtractedCitation, CaseBodyCache, CaseLastUpdate
from capdb.tasks import get_case_count_for_jur, get_court_count_for_jur, \
    get_reporter_count_for_jur, update_elasticsearch_for_vol, sync_case_body_cache_for_vol, \
    update_elasticsearch_from_queue, run_text_analysis_for_vol

import fabfile
from test_data.test_fixtures.helpers import get_timestamp, check_timestamps_changed, check_timestamps_unchanged, \
    set_case_text


@pytest.mark.django_db(databases=['capdb'])
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


@pytest.mark.django_db(databases=['capdb'])
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


@pytest.mark.django_db(databases=['capdb'])
def test_get_court_count_for_jur(court, jurisdiction):
    court.jurisdiction = jurisdiction
    court.save()

    results = get_court_count_for_jur(jurisdiction.id)
    assert results['total'] == Court.objects.filter(jurisdiction=jurisdiction).count()
    date = datetime.strptime(results['recorded'], "%Y-%m-%d %H:%M:%S.%f")
    assert date.day == datetime.now().day


@pytest.mark.django_db(databases=['capdb'])
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


@pytest.mark.django_db(databases=['capdb'])
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


@pytest.mark.django_db(databases=['capdb'])
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


@pytest.mark.django_db(databases=['capdb'])
def test_update_case_frontend_url_hyphen_cite(case):
    case.volume.volume_number = "123"
    case.volume.save()

    citation = case.citations.first()
    citation.cite = "123-Test-456"
    citation.save()
    fabfile.update_case_frontend_url(update_existing=True)
    case.refresh_from_db()
    assert case.frontend_url == "/test/123/456/%s/" % citation.case_id


@pytest.mark.django_db(databases=['capdb'])
def test_update_case_frontend_url_bad_cite(case):
    citation = case.citations.first()
    citation.cite = "BAD"
    citation.save()
    fabfile.update_case_frontend_url(update_existing=True)
    case.refresh_from_db()
    assert case.frontend_url == "/%s/%s/%s/%s/" % (case.reporter.short_name_slug, case.volume.volume_number, case.first_page, citation.case_id)


@pytest.mark.django_db(databases=['capdb'])
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


@pytest.mark.django_db(databases=['capdb'])
def test_extract_citations(reset_sequences, case_factory, elasticsearch, client):
    paragraph_1 = """
        correct: Foo v. Bar, 1 U.S. 1, 12 (2000) (overruling).
        extra cruft matched: 2 F.-'Supp.- 2
        custom reporters: 125 Yt. 152
        statutes: Ala. Code § 92.979
        law journals: 1 Minn. L. Rev. 1
    """
    paragraph_2 = """
        normalized: 2 US 2
        short cites: id. 1 U.S. at 153.
        ignored, too much cruft: 125 f. supp.-' 152
    """
    case_factory(citations__cite="1 U.S. 1", decision_date=datetime(1900, 1, 1))
    case_factory(citations__cite="2 U.S. 2", decision_date=datetime(1900, 1, 1))
    case_factory(citations__cite="2 U.S. 2", decision_date=datetime(1900, 1, 1))

    case = case_factory(decision_date=datetime(2000, 1, 1))
    set_case_text(case, paragraph_1, text3=paragraph_2)
    case.sync_case_body_cache()
    update_elasticsearch_from_queue()

    # check html
    assert """
    <p id="b83-6">
        correct: Foo v. Bar, <a href="http://cite.case.test:8000/us/1/1/#p12" class="citation" data-index="0" data-case-ids="1">1 U.S. 1</a>, 12 (2000) (overruling).
        extra cruft matched: <a href="http://cite.case.test:8000/citations/?q=2%20F.%20Supp.%202" class="citation" data-index="1">2 F.-'Supp.- 2</a>
        custom reporters: <a href="http://cite.case.test:8000/citations/?q=125%20Vt.%20152" class="citation" data-index="2">125 Yt. 152</a>
        statutes: <a href="http://cite.case.test:8000/citations/?q=Ala.%20Code%20%C2%A7%2092.979" class="citation" data-index="3">Ala. Code § 92.979</a>
        law journals: <a href="http://cite.case.test:8000/citations/?q=1%20Minn.%20L.%20Rev.%201" class="citation" data-index="4">1 Minn. L. Rev. 1</a>
    </p>
    <aside data-label="1" class="footnote" id="footnote_1_1">
      <a href="#ref_footnote_1_1">1</a>
      <p id="b83-11">
        normalized: <a href="http://cite.case.test:8000/us/2/2/" class="citation" data-index="5" data-case-ids="2,3">2 US 2</a>
        short cites: <a href="http://cite.case.test:8000/us/2/2/" class="citation" data-index="6" data-case-ids="2,3">id.</a> <a href="http://cite.case.test:8000/us/1/1/#p12" class="citation" data-index="7" data-case-ids="1">1 U.S. at 153</a>.
        ignored, too much cruft: 125 f. supp.-' 152
    </p>
    </aside>
    """.strip() in case.body_cache.html

    # check ExtractedCites entries
    extracted_cites_fields = [
        'cite', 'reporter', 'normalized_cite', 'rdb_cite', 'rdb_normalized_cite', 'cited_by_id', 'target_case_id',
        'target_cases', 'groups', 'metadata', 'pin_cites', 'category', 'weight', 'year',
    ]
    extracted_cites = [{f: getattr(e, f) for f in extracted_cites_fields} for e in case.extracted_citations.order_by('id').filter(cite__in=['1 U.S. 1', '2 US 2'])]
    expected_extracted_cites = [
        {
            'cite': '1 U.S. 1', 'reporter': 'U.S.', 'normalized_cite': '1us1', 'rdb_cite': '1 U.S. 1',
            'rdb_normalized_cite': '1us1', 'cited_by_id': 4, 'target_case_id': 1, 'target_cases': [1],
            'category': 'reporters:federal', 'weight': 2, 'year': 2000,
            'groups': {'page': '1', 'volume': '1', 'reporter': 'U.S.'},
            'metadata': {'year': '2000', 'court': 'scotus', 'pin_cite': '12', 'defendant': 'Bar', 'plaintiff': 'Foo', 'parenthetical': 'overruling'},
            'pin_cites': [{'page': '12', 'parenthetical': 'overruling'}, {'page': '153'}],
        },
        {
            'cite': '2 US 2', 'reporter': 'U.S.', 'normalized_cite': '2us2', 'rdb_cite': '2 U.S. 2',
            'rdb_normalized_cite': '2us2', 'cited_by_id': 4, 'target_case_id': None, 'target_cases': [2, 3],
            'category': 'reporters:federal', 'weight': 2, 'year': None,
            'groups': {'page': '2', 'volume': '2', 'reporter': 'US'},
            'metadata': {'court': 'scotus'},
            'pin_cites': [],
        }]
    assert extracted_cites == expected_extracted_cites

    # check API response
    case_json = client.get(api_reverse("cases-detail", args=[case.id])).json()

    assert case_json['cites_to'] == [
        {'cite': '1 U.S. 1', 'category': 'reporters:federal', 'reporter': 'U.S.', 'case_ids': [1], 'weight': 2, 'opinion_id': 0,
         'year': 2000, 'pin_cites': [{'page': '12', 'parenthetical': 'overruling'}, {'page': '153'}]},
        {'cite': "2 F.-'Supp.- 2", 'category': 'reporters:federal', 'reporter': 'F. Supp.', 'opinion_id': 0},
        {'cite': '125 Yt. 152', 'category': 'reporters:state', 'reporter': 'Vt.', 'opinion_id': 0},
        {'cite': 'Ala. Code § 92.979', 'category': 'laws:leg_statute', 'reporter': 'Ala. Code', 'opinion_id': 0},
        {'cite': '1 Minn. L. Rev. 1', 'category': 'journals:journal', 'reporter': 'Minn. L. Rev.', 'opinion_id': 0},
        {'cite': '2 US 2', 'category': 'reporters:federal', 'reporter': 'U.S.', 'case_ids': [2, 3], 'weight': 2, 'opinion_id': 0},
    ]

    # modify a cite --
    # make sure IDs of unchanged cites are still the same
    paragraph_1 = paragraph_1.replace("1 Minn. L. Rev. 1", "1 Minn. L. Rev. 1 (parenthetical)")
    old_id = ExtractedCitation.objects.get(cite="1 Minn. L. Rev. 1").id
    old_ids = ExtractedCitation.objects.values_list('id', flat=True)
    set_case_text(case, paragraph_1)
    case.sync_case_body_cache()
    new_id = ExtractedCitation.objects.get(cite="1 Minn. L. Rev. 1").id
    new_ids = ExtractedCitation.objects.values_list('id', flat=True)
    assert new_id != old_id
    assert set(new_ids) == (set(old_ids) | {new_id}) - {old_id}


@pytest.mark.django_db(databases=['capdb'])
def test_update_elasticsearch_for_vol(three_cases, volume_metadata, django_assert_num_queries, elasticsearch):
    with django_assert_num_queries(select=2, update=1):
        update_elasticsearch_for_vol(volume_metadata.barcode)


@pytest.mark.django_db(databases=['capdb'])
def test_sync_case_body_cache_for_vol(volume_metadata, case_factory, django_assert_num_queries, elasticsearch):
    cases = [case_factory(volume=volume_metadata) for c in range(3)]

    # full sync
    CaseBodyCache.objects.update(text='blank')
    with django_assert_num_queries(select=7, update=2, insert=1):
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


@pytest.mark.django_db(databases=['capdb'], transaction=True)
def test_run_text_analysis(reset_sequences, case):
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


@pytest.mark.django_db(databases=['capdb'])
def test_export_citation_graph(case_factory, tmpdir, elasticsearch, citation_factory, jurisdiction_factory):
    output_folder = Path(str(tmpdir))

    (
        cite_from, cite_to, different_jur_cite, cite_to_aka, another_cite_to,
        cite_not_in_cap, duplicate_cite, future_cite
    ) = ["%s U.S. %s" % (i, i) for i in range(1, 9)]

    jur1, jur2, jur3 = [jurisdiction_factory() for _ in range(3)]

    # cases
    case_from = case_factory(citations__cite=cite_from, decision_date=datetime(2000, 1, 1), jurisdiction=jur1)
    case_to = case_factory(citations__cite=cite_to, decision_date=datetime(1990, 1, 1), jurisdiction=jur1)
    citation_factory(cite=cite_to_aka, case=case_to)
    another_case_to = case_factory(citations__cite=another_cite_to, decision_date=datetime(1990, 1, 1), jurisdiction=jur3)
    different_jur_case = case_factory(citations__cite=different_jur_cite, decision_date=datetime(2000, 1, 1), jurisdiction=jur2)
    [case_factory(citations__cite=duplicate_cite, jurisdiction=jur1) for _ in range(3)]  # ambiguous cases
    case_factory(citations__cite=future_cite, decision_date=datetime(2010, 1, 1), jurisdiction=jur1)  # future case

    # case text to extract
    set_case_text(case_from, f"""
        Cite to self ignored during extraction: {cite_from}
        Parallel cite to another case included once: {cite_to}, {cite_to_aka}
        Cite to another case: {another_cite_to}
        Duplicate cite to another case: {another_cite_to}
        Ambiguous cites not included: {duplicate_cite}
        Unknown cites excluded: {cite_not_in_cap}
        Cites into the future excluded: {future_cite}
    """)
    set_case_text(different_jur_case, f"""
        Cite to case: {cite_to}
    """)

    # extract cites
    case_from.sync_case_body_cache()
    different_jur_case.sync_case_body_cache()

    # all cites found
    extracted = case_from.extracted_citations.all()
    assert set(e.cite for e in extracted) == {
        cite_to, another_cite_to,
        duplicate_cite, cite_not_in_cap, future_cite
    }

    # perform export
    fabfile.export_citation_graph(output_folder=str(output_folder))

    # check citations.csv.gz
    with gzip.open(str(output_folder / "citations.csv.gz"), 'rt') as f:
        results = list(csv.reader(f))
    assert len(results) == 2
    assert results[0][0] == str(case_from.id)
    assert len(results[0][1:]) == 2
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


@pytest.mark.django_db(databases=['capdb'], transaction=True)
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


@pytest.mark.django_db(databases=['capdb'])
def test_update_elasticsearch_from_queue(case, elasticsearch):
    case.name_abbreviation = 'New Name'
    case.save()
    assert list(CaseLastUpdate.objects.values_list('case_id', 'indexed')) == [(case.id, False)]
    update_elasticsearch_from_queue()
    assert list(CaseLastUpdate.objects.values_list('case_id', 'indexed')) == [(case.id, True)]
    assert CaseDocument.get(case.pk).name_abbreviation == 'New Name'

    # case gets removed when in_scope changes
    case.duplicative = True
    case.save()
    update_elasticsearch_from_queue()
    with pytest.raises(NotFoundError):
        CaseDocument.get(case.pk)
