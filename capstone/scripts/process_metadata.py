from datetime import datetime
from scripts.helpers import parse_xml
import re

def get_case_metadata(case_xml):
    parsed = parse_xml(case_xml)
    if parsed('duplicative|casebody'):
        first_page = int(parsed('duplicative|casebody').attr.firstpage)
        last_page = int(parsed('duplicative|casebody').attr.lastpage)
        volume_barcode = re.search('\/images\/([0-9a-zA-Z]+)_', case_xml)[1]
        return {
            'duplicative': True,
            'first_page': first_page,
            'last_page': last_page,
            'volume_barcode': volume_barcode,
        }   

    citation = parsed('case|citation').text().strip()
    citation_type = parsed('case|citation').attr.category
    cite_parts = citation.split(" ")
    volume, reporter, first_page = cite_parts[0], " ".join(cite_parts[1:-1]), cite_parts[-1]
    volume_barcode = parsed('case|case').attr('caseid').split("_")[0]

    if parsed('case|court').attr('jurisdiction'):
        jurisdiction = parsed('case|court').attr('jurisdiction').strip()
    else:
        print("Blank J!")
        print(parsed('case|court').html())
        jurisdiction = None

    if parsed('casebody|casebody').attr.lastpage.isdigit():
        last_page = int(parsed('casebody|casebody').attr.lastpage)
    else:
        last_page = None

    if not first_page:
        first_page = int(parsed('casebody|casebody').attr.firstpage)

    decision_date_original = parsed('case|decisiondate').text()
    decision_date = decision_datetime(decision_date_original)

    docket_number = parsed('case|docketnumber').text()

    court = {
        'name_abbreviation': parsed('case|court').attr.abbreviation,
        'name': parsed('case|court').text(),
    }

    return {
        'jurisdiction': jurisdiction,
        'citation': citation,
        'citation_type': citation_type,
        'reporter': reporter,
        'first_page': first_page,
        'last_page': last_page,
        'decision_date_original': decision_date_original,
        'decision_date': decision_date,
        'court': court,
        'docket_number': docket_number,
        'volume': volume,
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
