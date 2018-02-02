from capdb.models import CaseXML
from django.db import transaction
from scripts.helpers import parse_xml, nsmap, serialize_xml

"""
    This is obviously (mostly) purpose-built code for the judges tag update, 
    but I'm leaving the names pretty generic. I think we'll have more tasks
    like this in the future which we'll run from the command line, and I'm
    hoping that there will be enough commonality between those tasks to have
    some nice, generalizable code to put in there which will make our lives
    easier.
"""


def rename_casebody_tags_from_json_id_list(parsed_json, tag_name=None):
    with transaction.atomic():
        updated_records = 0
        for element in parsed_json:
            if tag_name is None:
                tag_name = element['tag']
            
            case = CaseXML.objects.get(metadata_id__case_id=element['caseid'])
            parsed_case = parse_xml(case.orig_xml)
            xml_element = parsed_case('casebody|*#' + element['id'])
            if xml_element == []:
                raise Exception("There is no case element with id {} in {}".format(element['id'], element['caseid']))
            xml_element[0].tag = "{{{}}}{}".format(nsmap['casebody'], tag_name)
            case.orig_xml = serialize_xml(parsed_case)
            xml_element = parsed_case('casebody|*#' + element['id'])
            case.save()
            updated_records += 1
        return updated_records