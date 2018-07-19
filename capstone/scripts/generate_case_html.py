from lxml import etree
from scripts.helpers import parse_xml
import re

tag_map = {  "author": "p", "opinion" : "article", "casebody" : "section",
             "citation": "p", "correction": "aside", "court": "p",
             "decisiondate": "p", "disposition": "p", "docketnumber": "p",
             "headnotes": "aside", "history": "p", "otherdate": "p",
             "parties": "h4", "seealso": "aside", "summary": "aside",
             "syllabus": "p", "footnote": "aside", "attorneys": "p",
             "judges": "p", "bracketnum": "a", "footnotemark": "a",
             "pagebreak": "br"}


# these styles will only be applied if case_body_only is explicitly set to false
bulma_class_map = {  "author": "title is-5", "opinion" : "section is-large", "casebody" : "container",
             "citation": "tag is-link", "correction": "tag is-warning", "court": "",
             "decisiondate": "subtitle is-5 has-text-centered", "disposition": "tile", "docketnumber": "",
             "headnotes": "tile", "history": "tile", "otherdate": "",
             "parties": "title is-4 has-text-centered", "seealso": "", "summary": "tile",
             "syllabus": "tile", "footnote": "box", "attorneys": "subtitle is-5 has-text-centered",
             "judges": "subtitle is-5 has-text-centered", "bracketnum": "", "footnotemark": "",
             "pagebreak": ""}

style = """ .headnotes::before {
    content: "Headnote: ";
    font-weight: bold;
    margin-right: 10px;
} 
.summary::before {
    content: "Summary: ";
    font-weight: bold;
    margin-right: 10px;
} 
.history::before {
    content: "History: ";
    font-weight: bold;
    margin-right: 10px;
} 

.disposition::before {
    content: "Disposition: ";
    font-weight: bold;
    margin-right: 10px;
} 

.syllabus::before {
    content: "Syllabus: ";
    font-weight: bold;
    margin-right: 10px;
} 

.author::before {
    content: "Author: ";
} 

.opinion::before {
    content: "Opinion";
    font-weight: bold;
} 

.opinion > p {
margin-bottom: 15px;
} 

.casebody > p {
margin-left: 25px;
margin-top: 10px;
} 

.footnote > p {
font-size: 0.75rem;
margin-bottom: 8px;
} 

article.opinion {
padding-top: 20px !important;
}

aside.footnote {
padding-top: 8px;
padding-left: 8px;
padding-right: 8px;
padding-bottom: 2px;
}
#top-citation {
    margin-left: 0 auto;
    margin-right: 0 auto;
    text-align: center;
}
"""

# these will pull out the headnotes number and corresponding bracketnum
bracketnum_number = re.compile(r'\d')
headnotes_number = re.compile(r'^(\d+).*')


def generate_html(case_xml, tag_map=tag_map, case_body_only=True):
    """
    converts case xml to html
    """
    parsed_xml = parse_xml(case_xml)

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

        element_text_copy = element.text

        if element_text_copy is None and tag != 'pagebreak':
            element_text_copy = element.getchildren()[0].text

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
            number_match = headnotes_number.match(element_text_copy)
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
            element.attrib['href'] = "#footnote_" + element_text_copy
        elif tag == "bracketnum":
            # point to the anchor in the headnote
            element.tag = "a"
            element.attrib['href'] = "#headnote_" + bracketnum_number.search(element_text_copy).group(0)
        elif tag == "pagebreak":
            # point to the anchor in the headnote
            element.attrib['style'] = "page-break-before: always"

        # apply the bulma styles
        if not case_body_only and tag in bulma_class_map and bulma_class_map[tag] is not "":
            element.attrib['class'] = "{} {}".format(bulma_class_map[tag], element.attrib['class'])

    # change the properties of the casebody tag itself
    casebody[0].tag = tag_map['casebody']
    for attribute in casebody[0].attrib:
        if attribute == 'class':
            continue
        casebody[0].attrib['data-' + attribute] = casebody[0].attrib[attribute]
        casebody[0].attrib.pop(attribute)

    # return if we only need the unstyled case body snippet
    if case_body_only is True:
        # return a copy of the string with the namepsaces stripped
        return str(re.sub(r' xmlns(:xlink)?="http://[^"]+"', '', str(casebody)))

    # add in the surrounding HTML
    pre_case_body = """<!doctype html>\n\n<html lang="en">\n\t<head>\n\t\t<title>CAPAPI: {0}</title>\n\t</head>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.1/css/bulma.min.css" />
    <style>{1}</style>
    \t<body>\n\t\t<h2 id="top-citation" class="subtitle is-5">{0}</h2>""".format(parsed_xml('case|citation')[0].text, style)

    post_case_body = "</body></html>"


    return "{}{}{}".format(pre_case_body, str(re.sub(r' xmlns(:xlink)?="http://[^"]+"', '', str(casebody))), post_case_body)
