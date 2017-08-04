from datetime import datetime
from pyquery import PyQuery as pq
from scripts.helpers import nsmap


def get_case_metadata(case_xml):
    parsed = pq(case_xml, namespaces=nsmap)
    jurisdiction = parsed('case|court').attr('jurisdiction').strip()
    citation = parsed('case|citation').text().strip()
    citation_type = parsed('case|citation').attr.category
    cite_parts = citation.split(" ")
    volume, reporter, first_page = cite_parts[0], " ".join(cite_parts[1:-1]), cite_parts[-1]
    last_page = int(parsed('casebody|casebody').attr.lastpage)

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
    }


def decision_datetime(decision_date_text):
    try:
        return datetime.strptime(decision_date_text, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(decision_date_text, '%Y-%m')
        except ValueError:
            return datetime.strptime(decision_date_text, '%Y')
