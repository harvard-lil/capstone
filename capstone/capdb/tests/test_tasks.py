from pathlib import Path

import pytest
import bagit
import zipfile
import os
import gzip
from django.db import connection, utils
import json

from capdb.models import CaseMetadata
from capdb.tasks import create_case_metadata_from_all_vols
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

@pytest.mark.django_db
def test_bag_jurisdiction(case_xml, tmpdir):
    # get the jurisdiction of the ingested case
    jurisdiction = case_xml.metadata.jurisdiction
    # bag the jurisdiction
    fabfile.bag_jurisdiction(jurisdiction.name, zip_directory=tmpdir)
    # validate the bag
    bag_path = str(tmpdir / jurisdiction.slug)
    with zipfile.ZipFile(bag_path + '.zip') as zf:
        zf.extractall(str(tmpdir))
    bag = bagit.Bag(bag_path)
    bag.validate()

@pytest.mark.django_db
def test_bag_reporter(case_xml, tmpdir):
    # get the jurisdiction of the ingested case
    reporter = case_xml.metadata.reporter
    # bag the reporter
    fabfile.bag_reporter(reporter.full_name, zip_directory=tmpdir)
    # validate the bag
    bag_path = next(Path(str(tmpdir)).glob("*.zip"))
    with zipfile.ZipFile(str(bag_path)) as zf:
        zf.extractall(str(tmpdir))
    bag = bagit.Bag(str(bag_path.with_suffix('')))
    bag.validate()

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
    cursor = connection.cursor()
    try:
        cursor.execute("create extension if not exists pg_stat_statements;")
        fabfile.show_slow_queries()
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "capstone slow query report" in output['text']
    except utils.OperationalError:
        pytest.skip("pg_stat_statements is not in shared_preload_libraries")
