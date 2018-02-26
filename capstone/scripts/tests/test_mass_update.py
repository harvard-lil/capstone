import pytest
from scripts import mass_update
from scripts.helpers import parse_xml
from capdb.models import CaseXML

@pytest.mark.django_db
def test_rename_tag_by_json(valid_mass_casebody_tag_rename, ingest_case_xml):
    """
        Tests the mass_update method that will rename all of the tags specified 
        in a json file to the tag name specified as the second argument in the 
        function call.

        I'm not actually using the results from ingest_case_xml but it's a
        convenient way to get all of the other ingest processes to run.
    """

    tag_name = "judges"
    assert mass_update.rename_casebody_tags_from_json_id_list(valid_mass_casebody_tag_rename, tag_name) == 2

    for element in valid_mass_casebody_tag_rename:
        case = CaseXML.objects.get(metadata__case_id=element['caseid'])
        parsed_case = parse_xml(case.orig_xml)
        xml_element = parsed_case('casebody|*#' + element['id'])
        assert xml_element[0].tag == '{}{}'.format('{http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1}', tag_name)


@pytest.mark.django_db
def test_rename_tag_by_json_invalid_raise(invalid_mass_casebody_tag_rename, ingest_case_xml):
    """
        This makes sure rename_casebody_tags_from_json_id_list dies, thereby
        triggering a complete rollback, if it encounters an element it can't
        locate in a specified file.

        I'm not actually using the results from ingest_case_xml but it's a
        convenient way to get all of the other ingest processes to run.
    """
    with pytest.raises(Exception, match='There is no case element with id b178-7 in 32044061407086_0001'):
        mass_update.rename_casebody_tags_from_json_id_list(invalid_mass_casebody_tag_rename, "judges")