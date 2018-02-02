from lxml import etree
from scripts.helpers import parse_xml
import re

tag_map = {  "author": "p", "opinion" : "article", "casebody" : "section",
             "citation": "h2", "correction": "aside", "court": "h3",
             "decisiondate": "p", "disposition": "p", "docketnumber": "p",
             "headnotes": "aside", "history": "p", "otherdate": "p",
             "parties": "h4", "seealso": "aside", "summary": "aside",
             "syllabus": "p", "footnote": "aside", "attorneys": "p",
             "judges": "p", "bracketnum": "a", "footnotemark": "a" }

# these will pull out the headnotes number and corresponding bracketnum
bracketnum_number = re.compile(r'\d')
headnotes_number = re.compile(r'^(\d+).*')

def generate_html(case_xml, tag_map=tag_map):
    parsed_xml = parse_xml(case_xml.orig_xml)

    # give a descriptive error for duplicative cases
    if parsed_xml('duplicative|casebody'):
        return "<h1 class='error'>This case is duplicative and was not fully \
        processed. It should be available in the original, non-regional \
        reporter.</h1>"
    casebody = parsed_xml("casebody|casebody")
    casebody_tree = casebody[0]


    # traverse the casebody tree and convert elements
    for element in casebody_tree.iter():

        # skip any anchor tags we generated
        if 'class' in element.attrib:
            if element.attrib['class'] == 'footnote_anchor' or element.attrib['class'] == 'headnote_anchor':
                continue

        # remove the namespace from the tag name
        tag = element.tag.split('}')[1]

        # for every attribute except id, turn it into an accepted data-* attribute
        for attribute in element.attrib:
            if attribute == 'id':
                continue
            element.attrib['data-' + attribute] = element.attrib[attribute]
            element.attrib.pop(attribute)

        # rename the tag based on the tag map, and set the class to the original tag name
        # e.g. <author> becomes <p class="author">
        if tag in tag_map:
            element.attrib['class'] = tag
            element.tag = tag_map[tag]

        # create internal links
        if tag == "footnote":
            # this anchor allows the footnotemark to link to the footnote
            anchor = etree.Element("a")
            anchor.attrib["id"] = "footnote_" + element.attrib['data-label']
            anchor.text = " "
            anchor.attrib['class'] = "footnote_anchor"
            element.append(anchor)
        elif tag == "headnotes":
            # this anchor allows the bracketnum to link to the proper headnote, if it exists
            number_match = headnotes_number.match(element.text)
            if number_match:
                number = number_match.groups(1)[0]
                anchor = etree.Element("a")
                anchor.attrib["id"] = "headnote_" + number
                anchor.attrib['class'] = "headnote_anchor"
                anchor.text = " "
                element.append(anchor)
        elif tag == "footnotemark":
            # point to the anchor in the footnote
            element.tag = "a"
            element.attrib['href'] = "#footnote_" + element.text
        elif tag == "bracketnum":
            # point to the anchor in the headnote
            element.tag = "a"
            element.attrib['href'] = "#headnote_" + bracketnum_number.search(element.text).group(0)

    # change the properties of the casebody tag itself
    casebody[0].tag = tag_map['casebody']
    for attribute in casebody[0].attrib:
        casebody[0].attrib['data-' + attribute] = casebody[0].attrib[attribute]
        casebody[0].attrib.pop(attribute)

    # return a copy of the string with the namepsaces stripped
    return str(re.sub(r' xmlns(:xlink)?="http://[^"]+"', '', str(casebody)))