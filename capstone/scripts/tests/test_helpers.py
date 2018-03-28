import re
import pytest
from scripts.helpers import serialize_xml, parse_xml
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
    assert len(styled_case("casebody|em")) == 24
    assert len(styled_case("casebody|strong")) == 7
    assert '__TAG' not in case_xml.orig_xml


@pytest.mark.django_db
def test_merge_alto_non_strict_case(ingest_case_xml):
    # testing non-strict processing with a case that has some character mismatches.
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044057892259_0001")
    styled_case = parse_xml(generate_styled_case_xml(case_xml, False))
    assert len(styled_case("casebody|em")) == 9
    assert len(styled_case("casebody|strong")) == 7
    assert '__TAG' not in case_xml.orig_xml

@pytest.mark.django_db
def test_merge_extra_char_exception(ingest_case_xml):
    # testing exceptions on character mismatches.
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044057892259_0001")
    with pytest.raises(Exception, match=r'Character discrepency between ALTO \("matter"\) and CaseMETS \("­matte"\)'):
        generate_styled_case_xml(case_xml)

@pytest.mark.django_db
def test_merge_dup_exception(ingest_case_xml):
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044061407086_0001")
    with pytest.raises(Exception, match=r'Duplicative case: no casebody data to merge'):
        generate_styled_case_xml(case_xml)

@pytest.mark.django_db
def test_validate_alto_casemets_dup(ingest_case_xml):
    results = validate(CaseXML.objects.get(metadata_id__case_id="32044061407086_0001"))
    assert results == {'problems': [], 'results': 'duplicative', 'status': 'ok', 'case': '32044061407086_0001'}

@pytest.mark.django_db
def test_validate_alto_casemets_clean(ingest_case_xml):
    results = validate(CaseXML.objects.get(metadata_id__case_id="32044057891608_0001"))
    assert results == {'results': 'encountered 0 problems', 'case': '32044057891608_0001', 'problems': [], 'status': 'ok'}

@pytest.mark.django_db
def test_validate_alto_casemets_dirty(ingest_case_xml):
    results = validate(CaseXML.objects.get(metadata_id__case_id="32044057892259_0001"))
    assert results == {'case': '32044057892259_0001', 'status': 'warning', 'results': 'encountered 2 problems', 'problems': [{'description': 'extra char in case_mets? match found in current alto', 'alto': {'next': {'ST_17.1.8.3': 'in'}, 'current': {'ST_17.1.8.1': 'matter'}, 'prev': None, 'current_character': {'ST_17.1.8.1': 'm'}}, 'casemets': {'current': '\xadmatte', 'snippet': 'tion of the subject-\xadmatter in controver', 'current_character': '\xad'}}, {'description': 'extra char in alto? match found subsequent alto element', 'alto': {'next': {'ST_19.1.11.9': ';'}, 'current': {'ST_19.1.11.7': '113\xad'}, 'prev': None, 'current_character': {'ST_19.1.11.7': '\xad'}}, 'casemets': {'current': '; Ca', 'snippet': 'Strobel, 24 Ill. 113; Carpenter v. Wells', 'current_character': ';'}}]}

@pytest.mark.django_db
def test_validate_alto_casemets_error(ingest_case_xml):
    case_xml = CaseXML.objects.get(metadata_id__case_id="32044057891608_0001")
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    case_parent_tag = parsed_case_xml('casebody|parties')
    case_parent_tag.text("Jonathan Taylor, Propellant, v. Machael Sprankle, Applebees.")
    case_xml.orig_xml = serialize_xml(parsed_case_xml)
    case_xml.save(update_related=False)
    results = validate(case_xml)
    assert results == {'status': 'error', 'problems': [{'description': 'Unspecified Mismatch.', 'casemets': {'current_character': 'P', 'snippet': 'Jonathan Taylor, Propellant, v. Macha', 'current': 'Propellant'}, 'alto': {'current_character': {'ST_17.2.1.5': 'A'}, 'current': {'ST_17.2.1.5': 'Appellant,'}, 'prev': None, 'next': {'ST_17.2.1.7': 'v.'}}}, {'description': 'Unspecified Mismatch.', 'casemets': {'current_character': 'P', 'snippet': 'Jonathan Taylor, Propellant, v. Macha', 'current': 'Pr'}, 'alto': {'current_character': {'ST_17.2.1.7': 'v'}, 'current': {'ST_17.2.1.7': 'v.'}, 'prev': None, 'next': {'ST_17.2.1.9': 'Michael'}}}], 'results': 'gave up after 2 consecutive bad words', 'case': '32044057891608_0001'}
