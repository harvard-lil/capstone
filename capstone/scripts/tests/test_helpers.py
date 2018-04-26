import re
import pytest
from scripts.helpers import serialize_xml, parse_xml, extract_casebody
from scripts.generate_case_html import generate_html, tag_map
from scripts.merge_alto_style import generate_styled_case_xml
from scripts.compare_alto_case import validate
from capdb.models import CaseXML

def test_serialize_xml_should_not_modify_input_xml(unaltered_alto_xml):
    parsed = parse_xml(unaltered_alto_xml)

    # make a change
    parsed('[ID="b17-15"]').attr('ID', 'replace_me')

    # serialize parsed xml
    new_xml = serialize_xml(parsed)

    # undo the change for comparison
    assert b'replace_me' in new_xml  # make sure modification worked
    new_xml = new_xml.replace(b'replace_me', b'b17-15')

    # serialized xml should be identical
    assert unaltered_alto_xml == new_xml

@pytest.mark.django_db
def test_generate_html_tags(ingest_case_xml):
    for case in CaseXML.objects.all():
        parsed_case_xml = parse_xml(case.orig_xml)

        # shouldn't attempt to parse a duplicative case
        if parsed_case_xml('duplicative|casebody'):
            assert generate_html(case.orig_xml).startswith("<h1 class='error'>")
            continue
        casebody_tree = parsed_case_xml("casebody|casebody")[0]
        casebody_html = generate_html(case.orig_xml).replace('\n', '').replace('\r', '').replace('\t', ' ')

        for element in casebody_tree.iter():
            old_tag = element.tag.split("}")[1]
            new_tag = 'p' if old_tag == 'p' else tag_map[old_tag]

            if 'id' in element.attrib:
                id_search = r'<' + re.escape(new_tag) + r'[^>]*id="' + re.escape(element.attrib['id'])
                assert re.search(id_search, casebody_html, re.IGNORECASE) is not None
            else:
                class_search = r'<' + re.escape(new_tag) + r'[^>]*class="' + re.escape(old_tag)
                assert re.search(class_search, casebody_html, re.IGNORECASE) is not None

@pytest.mark.django_db
def test_generate_html_footnotes(ingest_case_xml):
    for case in CaseXML.objects.all():
        parsed_case_xml = parse_xml(case.orig_xml)

        # shouldn't attempt to parse a duplicative case
        if parsed_case_xml('duplicative|casebody'):
            assert generate_html(case.orig_xml).startswith("<h1 class='error'>")
            continue
        casebody_html = generate_html(case.orig_xml).replace('\n', '').replace('\r', '').replace('\t', ' ')

        for footnote in parsed_case_xml("casebody|footnote"):
            footnote_anchor = '<a id="footnote_{}" class="footnote_anchor">'.format(footnote.attrib['label'])
            footnote_element = '<a class="footnotemark" href="#footnote_{}">{}</a>'.format(footnote.attrib['label'], footnote.attrib['label'])
            assert footnote_anchor in casebody_html
            assert footnote_element in casebody_html

@pytest.mark.django_db
def test_merge_alto_case(ingest_case_xml):
    # testing strict, totally compliant case
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044057891608_0001")
    styled_case = parse_xml(generate_styled_case_xml(case_xml))
    assert len(styled_case("casebody|em")) == 23
    assert len(styled_case("casebody|strong")) == 11


@pytest.mark.django_db
def test_merge_alto_extra_char_exception(ingest_case_xml):
    # testing processing with a case that has some character mismatches.
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044057892259_0001")

    case_xml.orig_xml = case_xml.orig_xml.replace("</p>", "y</p>")
    alto_xml = case_xml.pages.first()
    alto_xml.orig_xml = alto_xml.orig_xml.replace('CONTENT="', 'CONTENT="x')
    alto_xml.save()

    # fails with strict
    with pytest.raises(Exception, match=r'Case text and alto text do not match'):
        generate_styled_case_xml(case_xml)

    # passes without strict
    styled_case = parse_xml(generate_styled_case_xml(case_xml, False))
    assert len(styled_case("casebody|em")) == 8
    assert len(styled_case("casebody|strong")) == 11


@pytest.mark.django_db
def test_merge_dup_exception(ingest_case_xml):
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044061407086_0001")
    with pytest.raises(Exception, match=r'Duplicative case: no casebody data to merge'):
        generate_styled_case_xml(case_xml)

@pytest.mark.django_db
def test_validate_alto_casemets_dup(ingest_case_xml):
    results = validate(CaseXML.objects.get(metadata_id__case_id="32044061407086_0001"))
    assert results['status'] == 'ok'
    assert results['results'] == 'duplicative'

@pytest.mark.django_db
def test_validate_alto_casemets_clean(ingest_case_xml):
    results = validate(CaseXML.objects.get(metadata_id__case_id="32044057891608_0001"))
    assert results['status'] == 'ok'
    assert results['results'] == 'clean'

@pytest.mark.django_db
def test_validate_alto_casemets_dirty(ingest_case_xml):
    results = validate(CaseXML.objects.get(metadata_id__case_id="32044057892259_0001"))
    assert results['status'] == 'warning'
    assert results['results'] == 'encountered 2 problems'
    problem_1 = {'alto': {'current': {'ST_17.1.8.1': 'matter'},
              'current_character': {'ST_17.1.8.1': 'm'},
              'next': {'ST_17.1.8.3': 'in'},
              'prev': None},
     'casemets': {'current': '\xadmatte',
                  'current_character': '\xad',
                  'snippet': 'tion of the subject-\xadmatter in controver'},
     'description': 'extra char in case_mets? match found in current alto'}
    problem_2 = {'alto': {'current': {'ST_19.1.11.7': '113\xad'},
              'current_character': {'ST_19.1.11.7': '\xad'},
              'next': {'ST_19.1.11.9': ';'},
              'prev': {'ST_19.1.11.5': 'Ill.'}},
     'casemets': {'current': '; Ca',
                  'current_character': ';',
                  'snippet': 'Strobel, 24 Ill. 113; Carpenter v. Wells'},
     'description': 'extra char in alto? match found subsequent alto element'}
    assert problem_1 in results['problems']
    assert problem_2 in results['problems']

@pytest.mark.django_db
def test_validate_alto_casemets_error(ingest_case_xml):
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044057891608_0001")
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    case_parent_tag = parsed_case_xml('casebody|parties')
    case_parent_tag.text("Jonathan Taylor, Propellant, v. Machael Sprankle, Applebees.")
    case_xml.orig_xml = serialize_xml(parsed_case_xml)
    case_xml.save(update_related=False)
    results = validate(case_xml)
    problem_1 = {'alto': {'current': {'ST_17.2.1.5': 'Appellant,'},
              'current_character': {'ST_17.2.1.5': 'A'},
              'next': {'ST_17.2.1.7': 'v.'},
              'prev': {'ST_17.2.1.3': 'Taylor,'}},
     'casemets': {'current': 'Propellant',
                  'current_character': 'P',
                  'snippet': 'Jonathan Taylor, Propellant, v. Macha'},
     'description': 'Unspecified Mismatch.'}
    problem_2 = {'alto': {'current': {'ST_17.2.1.7': 'v.'},
              'current_character': {'ST_17.2.1.7': 'v'},
              'next': {'ST_17.2.1.9': 'Michael'},
              'prev': {'ST_17.2.1.5': 'Appellant,'}},
     'casemets': {'current': 'Pr',
                  'current_character': 'P',
                  'snippet': 'Jonathan Taylor, Propellant, v. Macha'},
     'description': 'Unspecified Mismatch.'}
    assert results['status'] == 'error'
    assert results['results'] == 'gave up after 2 consecutive bad words'
    assert problem_1 in results['problems']
    assert problem_2 in results['problems']


@pytest.mark.django_db
def test_extract_casebody(ingest_case_xml):
    # extract_casebody should clean up quotation marks
    orig_xml = ingest_case_xml.orig_xml
    assert '\u2019' in orig_xml
    casebody = extract_casebody(orig_xml)
    assert '\u2019' not in casebody.text()
