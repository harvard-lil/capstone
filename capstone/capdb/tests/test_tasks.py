import lzma
from pathlib import Path
import pytest
import bagit
import zipfile
import os
import csv
import gzip
import json
from datetime import datetime
from django.db import connections, utils

from capdb.models import CaseMetadata, Court, Reporter, Citation, Jurisdiction, ExtractedCitation
from capdb.tasks import create_case_metadata_from_all_vols, get_case_count_for_jur, get_court_count_for_jur, get_reporter_count_for_jur, update_elasticsearch_for_vol

import fabfile


@pytest.mark.django_db
def test_create_case_metadata_from_all_vols(case_xml):
    # get initial state
    metadata_count = CaseMetadata.objects.count()
    case_id = case_xml.metadata.case_id

    # delete case metadata
    case_xml.metadata.delete()
    assert CaseMetadata.objects.count() == metadata_count - 1

    # recreate case metadata
    create_case_metadata_from_all_vols()

    # check success
    case_xml.refresh_from_db()
    assert CaseMetadata.objects.count() == metadata_count
    assert case_xml.metadata.case_id == case_id


def check_exports(case, filter_item, tmpdir):
    tmpdir = Path(str(tmpdir))

    # should have two exports
    exports = list(filter_item.case_exports.all())
    assert len(exports) == 2

    for export in exports:
        assert export.public is False

        # check bag format
        bag_path = Path(export.file_name).with_suffix('')
        with zipfile.ZipFile(export.file.open()) as zf:
            zf.extractall(str(tmpdir))
        bag = bagit.Bag(str(tmpdir / bag_path))
        bag.validate()

        # check data file
        with lzma.open(str(tmpdir / bag_path / 'data' / 'data.jsonl.xz')) as in_file:
            records = [json.loads(str(line, 'utf8')) for line in in_file if line]
        assert len(records) == 1
        assert records[0]['name'] == case.name
        if export.body_format == 'xml':
            assert records[0]['casebody']['data'].startswith('<?xml')
        else:
            assert 'opinions' in records[0]['casebody']['data']

        # clean up files
        # (this is hard to do with tmpdir, because the path is set by CaseExport.file.storage when pytest loads)
        export.file.delete(save=False)


@pytest.mark.django_db
def test_bag_jurisdiction(restricted_case, tmpdir, django_assert_num_queries, elasticsearch):

    jurisdiction = Jurisdiction.objects.get(pk=restricted_case.jurisdiction.id)
    # bag the jurisdiction
    with django_assert_num_queries(select=2, insert=2):
        fabfile.bag_jurisdiction(restricted_case.jurisdiction.name)
    check_exports(restricted_case, jurisdiction, tmpdir)


@pytest.mark.django_db
def test_bag_reporter(restricted_case, tmpdir, elasticsearch):
    reporter = Reporter.objects.get(pk=restricted_case.reporter.id)
    fabfile.bag_reporter(reporter.id)
    check_exports(restricted_case, reporter, tmpdir)


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
def test_update_case_frontend_url_hyphen_cite(case_metadata):
    case_metadata.volume.volume_number = "123"
    case_metadata.volume.save()

    citation = case_metadata.citations.first()
    citation.cite = "123-Test-456"
    citation.save()
    fabfile.update_case_frontend_url(update_existing=True)
    case_metadata.refresh_from_db()
    assert case_metadata.frontend_url == "/test/123/456/%s/" % citation.case_id


@pytest.mark.django_db
def test_update_case_frontend_url_bad_cite(case_metadata):
    citation = case_metadata.citations.first()
    citation.cite = "BAD"
    citation.save()
    fabfile.update_case_frontend_url(update_existing=True)
    case_metadata.refresh_from_db()
    assert case_metadata.frontend_url == "/%s/%s/%s/%s/" % (case_metadata.reporter.short_name_slug, case_metadata.volume.volume_number, case_metadata.first_page, citation.case_id)



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
    case.body_cache.text="""
        A12345678  # 8 digit A-number
        A123456789  # 9 digit A-number
        A-12345678  # 8 digit A-number with hyphen
        A — 123456789  # 9 digit A-number with mdash and spaces
    """
    case.no_index_redacted = {}
    case.body_cache.save()
    case.save()
    fabfile.redact_id_numbers()
    case.refresh_from_db()
    assert case.no_index_redacted == {
        'A12345678': 'AXXXXXXXX',
        'A — 123456789': 'A — XXXXXXXXX',
        'A123456789': 'AXXXXXXXXX',
        'A-12345678': 'A-XXXXXXXX',
    }


@pytest.mark.django_db
def test_extract_citations(case_factory, tmpdir, settings):
    settings.MISSED_CITATIONS_DIR = str(tmpdir)
    legitimate_cites = ["225 F.Supp. 552", "225 f supp 552"]
    illegitimate_cites = ["2 Dogs 3", "3 Dogs 4"]
    case = case_factory(body_cache__text=", some text, ".join(legitimate_cites+illegitimate_cites))
    fabfile.extract_all_citations()
    cites = list(ExtractedCitation.objects.all())
    assert set(c.cite for c in cites) == set(legitimate_cites)
    assert all(c.cited_by == case for c in cites)

    # check missed_citations files
    results = []
    for missed_file in Path(settings.MISSED_CITATIONS_DIR).glob('missed_citations-*.csv'):
        results.extend(list(csv.reader(missed_file.read_text().splitlines())))
    assert results == [[str(case.id), '1', '{"Dogs": 2}']]


@pytest.mark.django_db
def test_update_elasticsearch_for_vol(three_cases, volume_metadata, django_assert_num_queries):
    for case in three_cases:
        case.volume = volume_metadata
        case.save()
    with django_assert_num_queries(select=2, update=1):
        update_elasticsearch_for_vol(volume_metadata.barcode)
