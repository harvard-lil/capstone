import pytest

from django.core.files.storage import FileSystemStorage

from scripts import update_download_tsv
from capweb.templatetags.api_url import api_url


@pytest.mark.django_db(databases=['capdb'])
def test_cases_by_decision_date(case_factory, client, tmp_path, monkeypatch):
    dates = ["2000", "2000-04", "2000-04", "2000-04-15"]
    _ = [case_factory(decision_date_original=d) for d in dates]
    monkeypatch.setattr("scripts.update_download_tsv.download_files_storage", FileSystemStorage(location=str(tmp_path)))
    fs_storage = FileSystemStorage(location=str(tmp_path))

    update_download_tsv.cases_by_decision_date_tsv()

    file_contents = fs_storage.open(tmp_path / 'cases_by_decision_date.tsv').read()
    correct_contents = bytes('"2000"\t4\t"https://api.case.test:8000/v1/cases/?decision_date__gte=2000&decision_date__lte=2000-12-31"\r\n'
    '"2000-04"\t3\t"https://api.case.test:8000/v1/cases/?decision_date__gte=2000-04&decision_date__lte=2000-04-31"\r\n'
    '"2000-04-15"\t1\t"https://api.case.test:8000/v1/cases/?decision_date__gte=2000-04-15&decision_date__lte=2000-04-15"\r\n' , encoding='utf-8')
    assert file_contents == correct_contents

@pytest.mark.django_db(databases=['capdb'])
def test_cases_by_jurisdiction(jurisdiction, case_factory, client, tmp_path, monkeypatch):
    [case_factory(jurisdiction=jurisdiction) for i in range(3)]
    monkeypatch.setattr("scripts.update_download_tsv.download_files_storage", FileSystemStorage(location=str(tmp_path)))
    fs_storage = FileSystemStorage(location=str(tmp_path))

    update_download_tsv.cases_by_jurisdiction_tsv()

    file_contents = fs_storage.open(tmp_path / 'cases_by_jurisdiction.tsv').read()
    correct_contents = bytes('"{}"\t"{}"\t{}\t"{}"\t"{}"\r\n'.format(
        jurisdiction.name,
        jurisdiction.name_long,
        3,
        "{}?jurisdiction={}".format(api_url('cases-list'), jurisdiction.slug),
        "{}{}".format(api_url('jurisdiction-list'), jurisdiction.pk)), encoding='utf-8')
    assert file_contents == correct_contents


@pytest.mark.django_db(databases=['capdb'])
def test_cases_by_reporter(reporter, case_factory, client, tmp_path, monkeypatch):
    [case_factory(reporter=reporter) for i in range(3)]
    monkeypatch.setattr("scripts.update_download_tsv.download_files_storage", FileSystemStorage(location=str(tmp_path)))
    fs_storage = FileSystemStorage(location=str(tmp_path))

    update_download_tsv.cases_by_reporter_tsv()

    file_contents = fs_storage.open(tmp_path / 'cases_by_reporter.tsv').read()
    correct_contents = bytes('"{}"\t"{}"\t{}\t"{}"\t"{}"\r\n'.format(
        reporter.short_name,
        reporter.full_name,
        3,
        "{}?reporter={}".format(api_url('cases-list'), reporter.pk),
        "{}{}".format(api_url('reporter-list'), reporter.pk)
    ), encoding='utf-8')
    assert correct_contents in file_contents

