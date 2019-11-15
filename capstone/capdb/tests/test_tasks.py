import lzma
from pathlib import Path
import pytest
import bagit
import zipfile
import os
import gzip
from django.db import connections, utils
import json
from datetime import datetime

from capdb.models import CaseMetadata, Court, Reporter, Citation, Jurisdiction
from capdb.tasks import create_case_metadata_from_all_vols, get_case_count_for_jur, get_court_count_for_jur, get_reporter_count_for_jur

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
def test_bag_jurisdiction(non_whitelisted_case_document, tmpdir, django_assert_num_queries):

    jurisdiction = Jurisdiction.objects.get(pk=non_whitelisted_case_document.jurisdiction.id)
    # bag the jurisdiction
    with django_assert_num_queries(select=2, insert=2):
        fabfile.bag_jurisdiction(non_whitelisted_case_document.jurisdiction.name)
    check_exports(non_whitelisted_case_document, jurisdiction, tmpdir)


@pytest.mark.django_db
def test_bag_reporter(non_whitelisted_case_document, tmpdir):
    reporter = Reporter.objects.get(pk=non_whitelisted_case_document.reporter.id)
    fabfile.bag_reporter(reporter.id)
    check_exports(non_whitelisted_case_document, reporter, tmpdir)


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
    case_metadata = case_factory()
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