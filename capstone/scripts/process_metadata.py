from datetime import datetime
from scripts.helpers import parse_xml, resolve_namespace
import re

def get_case_metadata(case_xml):
    parsed = parse_xml(case_xml.replace('\xad', ''))

    # duplicative cases won't have a case section, so rather than using case.caseid we get the volume barcode from the
    # first alto file entry, and the case number from the casebody:
    alto_name = parsed('mets|fileGrp[USE="alto"] mets|FLocat')[0].attrib[resolve_namespace('xlink|href')].split('/')[-1]
    volume_barcode = re.match(r'([A-Za-z0-9_]+)_(un)?redacted([0-9_]*)', alto_name).group(1)
    case_number = parsed('mets|fileGrp[USE="casebody"] > mets|file').attr["ID"].split('_')[1]
    case_id = "%s_%s" % (volume_barcode, case_number)

    metadata = {
        'volume_barcode': volume_barcode,
        'case_id': case_id
    }
    if parsed('duplicative|casebody'):
        first_page = parsed('duplicative|casebody').attr.firstpage
        last_page = parsed('duplicative|casebody').attr.lastpage
        return dict(metadata, **{
            'duplicative': True,
            'first_page': first_page,
            'last_page': last_page,
        }), parsed

    citation_entries = parsed('case|case').find('case|citation')
    citations = [{
        'citation_type': cite.attrib['category'],
        'citation_text': cite.text,
        'is_duplicative': False
    } for cite in citation_entries]
    jurisdiction = parsed('case|court').attr('jurisdiction').strip()

    name = parsed('case|name').text()
    name_abbreviation = parsed('case|name').attr('abbreviation')

    first_page = parsed('casebody|casebody').attr.firstpage
    last_page = parsed('casebody|casebody').attr.lastpage

    decision_date_original = parsed('case|decisiondate').text()
    decision_date = parse_decision_date(decision_date_original)

    docket_number = parsed('case|docketnumber').text()

    court = {
        'name_abbreviation': parsed('case|court').attr.abbreviation,
        'name': parsed('case|court').text(),
    }

    judges = [judge.text for judge in parsed('casebody|judges')]
    attorneys = [attorney.text for attorney in parsed('casebody|attorneys')]
    parties = [party.text for party in parsed('casebody|parties')]
    opinions = [
        {
            'type': opinion.attr('type'),
            'author': opinion('casebody|author').text() or None,
        }
        for opinion in parsed.items('casebody|opinion')
    ]

    return dict(metadata, **{
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
        'duplicative': False,
        'judges': judges,
        'attorneys': attorneys,
        'parties': parties,
        'opinions': opinions
    }), parsed


def parse_decision_date(decision_date_text):
    try:
        try:
            return datetime.strptime(decision_date_text, '%Y-%m-%d').date()
        except ValueError as e:

            # if court used an invalid day of month (typically Feb. 29), strip day from date
            if e.args[0] == 'day is out of range for month':
                decision_date_text = decision_date_text.rsplit('-', 1)[0]

            try:
                return datetime.strptime(decision_date_text, '%Y-%m').date()
            except ValueError:
                return datetime.strptime(decision_date_text, '%Y').date()
    except Exception as e:
        # if for some reason we can't parse the date, just store None
        return None
