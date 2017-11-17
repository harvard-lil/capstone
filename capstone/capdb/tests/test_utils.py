import pytest
from capdb import utils
from capdb.models import Reporter, Jurisdiction
from scripts.helpers import parse_xml
from capdb.utils import update_case_alto_unified

@pytest.mark.django_db
def test_generate_unique_slug(ingest_metadata):
    unique_name = "Caselaw Access Project"

    slug1 = utils.generate_unique_slug(Reporter(), unique_name, field="full_name")
    assert slug1 == "caselaw-access-project"

    reporter = Reporter.objects.first()
    reporter_name = reporter.full_name
    slug2 = utils.generate_unique_slug(Reporter(), reporter_name, field="full_name")
    assert slug2 == utils.slugify(reporter_name)

    # method deals with collisions
    jurisdiction = Jurisdiction(name='New. State.')
    jurisdiction.slug = utils.generate_unique_slug(Jurisdiction(), jurisdiction.name)
    jurisdiction.save()

    new_unique_slug = utils.generate_unique_slug(Jurisdiction(), jurisdiction.name)
    assert new_unique_slug != jurisdiction.slug

@pytest.mark.django_db
def test_case_alto_modify_word(case_xml):
    updated_case = parse_xml(case_xml.orig_xml)
    updated_case('casebody|p[id="b17-6"]').text("The 4rgUm3nt in favor of the appellee rests wholly on the assumption that the judgment in the garnishee proceedings should be rendered in favor of the judgment debtor for the use of the judgment creditor, against the garnished party, for the whole amount due, and in case of failure to so render judgment for such amount and for a less amount than due, the balance over and above the amount of the judgment so rendered would be barred on the grounds of former recovery.")
    data_migration = update_case_alto_unified(case_xml, updated_case)
    assert 'ok' in data_migration
    assert '4rgUm3nt' in data_migration['ok']['case_xml_changed'][0]['changes'][0]['actions']['content']
    assert '4rgUm3nt' in data_migration['ok']['alto_xml_changed'][0]['changes'][2]['actions']['add_update']['CONTENT']

@pytest.mark.django_db
def test_case_alto_add_delete_tag(case_xml):
    pass

@pytest.mark.django_db
def test_case_alto_modify_tag(case_xml):
    pass

@pytest.mark.django_db
def test_case_alto_add_delete_word(case_xml):
    pass