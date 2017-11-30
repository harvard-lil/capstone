import pytest
from scripts.helpers import parse_xml
from scripts.data_migrations import generate_migration_from_case

@pytest.mark.django_db
def test_casebody_modify_word(case_xml):
    updated_case = parse_xml(case_xml.orig_xml)
    updated_case('casebody|p[id="b17-6"]').text("The 4rgUm3nt in favor of the appellee rests wholly on the assumption that the judgment in the garnishee proceedings should be rendered in favor of the judgment debtor for the use of the judgment creditor, against the garnished party, for the whole amount due, and in case of failure to so render judgment for such amount and for a less amount than due, the balance over and above the amount of the judgment so rendered would be barred on the grounds of former recovery.")
    data_migration = generate_migration_from_case(case_xml, updated_case)
    assert 'ok' in data_migration
    assert '4rgUm3nt' in data_migration['ok']['case_xml_changed'][0]['changes'][0]['actions']['content']
    assert '4rgUm3nt' == data_migration['ok']['alto_xml_changed'][0]['changes'][2]['actions']['add_update']['CONTENT']


@pytest.mark.django_db
def test_case_delete_tag(case_xml):
    updated_case = parse_xml(case_xml.orig_xml)
    updated_case('case|case').remove('case|decisiondate')
    data_migration = generate_migration_from_case(case_xml, updated_case)
    assert 'ok' in data_migration
    assert data_migration['ok']['case_xml_changed'][0]['changes'][0]['actions']['remove'] is True
"""
@pytest.mark.django_db
def test_casebody_delete_tag(case_xml):
    updated_case = parse_xml(case_xml.orig_xml)
    updated_case('casebody|casebody').remove('casebody|decisiondate')
    data_migration = generate_migration_from_case(case_xml, updated_case)
    assert 'ok' in data_migration
    assert data_migration['ok']['case_xml_changed'][0]['changes'][0]['actions']['remove'] is True

@pytest.mark.django_db
def test_case_add_tag(case_xml):
    updated_case = parse_xml(case_xml.orig_xml)
    updated_case('case|case').append('case|decisiondate')
    data_migration = generate_migration_from_case(case_xml, updated_case)
    assert 'ok' in data_migration
    assert data_migration['ok']['case_xml_changed'][0]['changes'][0]['actions']['create'] is True

@pytest.mark.django_db
def test_casebody_add_tag(case_xml):
    updated_case = parse_xml(case_xml.orig_xml)
    updated_case('case|case').remove('case|decisiondate')
    data_migration = generate_migration_from_case(case_xml, updated_case)
    assert 'ok' in data_migration
    assert data_migration['ok']['case_xml_changed'][0]['changes'][0]['actions']['create'] is True
@pytest.mark.django_db
def test_case_alto_modify_tag(case_xml):
    pass

@pytest.mark.django_db
def test_case_alto_add_delete_word(case_xml):
    pass
"""