from datetime import datetime
import re
from scripts.helpers import parse_xml


def get_case_metadata(case_xml):
    parsed = parse_xml(case_xml)
    volume_barcode = re.search(r'\/images\/([0-9a-zA-Z]+)_', case_xml)[1]
    if parsed('duplicative|casebody'):
        first_page = int(parsed('duplicative|casebody').attr.firstpage)
        last_page = int(parsed('duplicative|casebody').attr.lastpage)
        return {
            'duplicative': True,
            'first_page': first_page,
            'last_page': last_page,
            'volume_barcode': volume_barcode,
        }

    citation_entries = parsed('case|case').find('case|citation')
    citations = {cite.attrib['category']: cite.text for cite in citation_entries}
    jurisdiction = parsed('case|court').attr('jurisdiction').strip()
    
    if parsed('casebody|casebody').attr.lastpage.isdigit():
        last_page = int(parsed('casebody|casebody').attr.lastpage)
    else:
        last_page = None

    name = parsed('case|name').text()
    name_abbreviation = parsed('case|name').attr('abbreviation')

    first_page = int(parsed('casebody|casebody').attr.firstpage)

    decision_date_original = parsed('case|decisiondate').text()
    decision_date = decision_datetime(decision_date_original)

    docket_number = parsed('case|docketnumber').text()

    court = {
        'name_abbreviation': parsed('case|court').attr.abbreviation,
        'name': parsed('case|court').text(),
    }

    return {
        'name': name,
        'name_abbreviation': name_abbreviation,
        'jurisdiction': jurisdiction,
        'citations': citations,
        'first_page': first_page,
        'last_page': last_page,
        'decision_date_original': decision_date_original,
        'decision_date': decision_date,
        'court': court,
        'docket_number': docket_number,
        'volume_barcode': volume_barcode,
        'duplicative': False,
    }


def decision_datetime(decision_date_text):
    try:
        return datetime.strptime(decision_date_text, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(decision_date_text, '%Y-%m')
        except ValueError:
            return datetime.strptime(decision_date_text, '%Y')
