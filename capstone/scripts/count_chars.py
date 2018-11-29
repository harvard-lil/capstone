from collections import Counter

from celery import shared_task
from capdb.models import CaseXML
import json
from os import mkdir
from scripts.helpers import extract_casebody

def count_chars_in_all_cases(path):
    """
        iterate through all volumes, call celery task for each volume
    """
    query = CaseXML.objects.all()

    # if not updating existing, then only launch jobs for volumes with unindexed cases:

    # This will dump a json file for each case in the directory specified in path
    try:
        mkdir(path)
    except FileExistsError:
        pass
        # already exists. this will overwrite existing data, but unless the cases or script
        # have changed, it should be the same data.

    # launch a job for each volume:
    for cmd_id in query.values_list('pk', flat=True):
        count_case_chars.delay(cmd_id, path, write_to_disk=True)


@shared_task
def count_case_chars(case_xml_id, path, write_to_disk=False):
    """
        create or update cases for each volume
    """
    case_xml = CaseXML.objects.select_related('metadata__reporter', 'volume').get(pk=case_xml_id)
    case_metadata = case_xml.metadata
    reporter = case_metadata.reporter
    volume = case_metadata.volume
    charlist = list(case_xml.orig_xml)
    case_body_char_list = list(extract_casebody(case_xml.orig_xml).text())

    output = {}
    output['metadata_db_id'] = case_metadata.pk
    output['whole_xml_counts'] = Counter(charlist)
    output['casebody_text_no_soft_hyphen_counts'] = Counter(case_body_char_list)

    output['metadata'] = {}
    output['metadata']['case_id'] = case_metadata.case_id
    output['metadata']['name'] = case_metadata.name
    output['metadata']['reporter'] = reporter.short_name
    output['metadata']['volume'] = volume.volume_number
    output['metadata']['duplicative'] = case_metadata.duplicative
    output['metadata']['publication_year'] = volume.publication_year
    output['metadata']['publisher'] = volume.publisher
    output['metadata']['jurisdiction_name'] = case_metadata.jurisdiction_name
    output['metadata']['court_name'] = case_metadata.court_name

    if write_to_disk:
        f= open(mode='w', file="{}/{}.json".format(path, case_metadata.case_id))
        json.dump(output, f)
        f.close()
    else:
        return output
