from datetime import datetime
from pyquery import PyQuery as pq

namespaces = {
    'METS': 'http://www.loc.gov/METS/',
    'case': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case:v1',
    'casebody': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1',
    'volume': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Volume:v1',
    'xlink': 'http://www.w3.org/1999/xlink',
    'alto': 'http://www.loc.gov/standards/alto/ns-v3#',
}

def get_case_metadata(case_xml):
    parsed = pq(case_xml, namespaces=namespaces)
    jurisdiction = parsed('case|court').attr('jurisdiction').strip()
    citation = parsed('case|citation').text().strip()
    citation_type = parsed('case|citation').attr.category
    cite_parts = citation.split(" ")
    volume, reporter, first_page = cite_parts[0], " ".join(cite_parts[1:-1]), cite_parts[-1]
    last_page = int(parsed('casebody|casebody').attr.lastpage)

    if not first_page:
        first_page = int(parsed('casebody|casebody').attr.firstpage)

    original_decision_date = parsed('case|decisiondate').text()
    decision_date = decision_datetime(original_decision_date)

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
        'original_decision_date': original_decision_date,
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
