import re
import pytest
from scripts.helpers import serialize_xml, parse_xml
from scripts.generate_case_html import generate_html, tag_map
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
            assert generate_html(case).startswith("<h1 class='error'>")
            continue
        casebody_tree = parsed_case_xml("casebody|casebody")[0]
        casebody_html = generate_html(case).replace('\n', '').replace('\r', '').replace('\t', ' ')

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