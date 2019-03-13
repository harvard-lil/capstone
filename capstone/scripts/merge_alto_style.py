import difflib
import html
import re
from collections import defaultdict
from pyquery import PyQuery

from django.utils.encoding import force_str

from scripts.helpers import parse_xml, serialize_xml


### helpers

def split_string_and_insertions(string, pattern):
    """
        Given a string and a regex pattern, return the string without instances of the pattern, along with a dictionary
        of the locations of the pattern. For example, given "ab<el>cd</el>ef" and a pattern to extract tags,
        return "abcdef" and the dictionary {2: "<el>", 4: "</el>"}
    """
    new_string = ""
    index = 0
    insertions = defaultdict(list)
    parts = re.split(pattern, string)
    for i, part in enumerate(parts):
        if i % 2:
            insertions[index].append(part)
        else:
            index += len(part)
            new_string += part
    return new_string, insertions

def join_string_and_insertions(string, insertions):
    """
        Reverse the effects of split_string_and_insertions. Given a string and a set of insertions, return
        the combined string.
    """
    parts = []
    index = 0
    sorted_insertions = sorted(insertions.items(), key=lambda item: item[0])
    for i, insertion in sorted_insertions:
        parts.append(string[index:i])
        parts.extend(insertion)
        index = i
    parts.append(string[index:])
    return ''.join(parts)

# map styles in the alto header to casexml tags we're trying to insert:
styles = {
    'bold': {
        'open': '<strong>',
        'close': '</strong>',
    },
    'italics': {
        'open': '<em>',
        'close': '</em>',
    }
}

# regexes to strip added tags from existing casexml:
strip_style_tags_re = '|'.join(
    re.escape(tag)
    for style in styles.values()
    for tag in style.values()
)

strip_pagebreaks = r'<page\-number[a-zA-Z0-9= #\-"]*>\*\d+</page\-number>'

### main script

def generate_styled_case_xml(case_xml, strict=True):

    # strip added tags from existing casexml:
    stripped_xml = re.sub(strip_style_tags_re, '', re.sub(strip_pagebreaks, '', case_xml.orig_xml))
    parsed_case = parse_xml(stripped_xml)

    # dup cases have no casebody to style
    if parsed_case('duplicative|casebody'):
        raise Exception("Duplicative case: no casebody data to merge")

    # Build a dictionary of text blocks in the alto files, indexed by tagref, with their associated page styles if any.
    # Each key is a tagref, and each value is a list of tuples of lxml TextBlock element and associated page styles.
    # For example:
    #   text_blocks_by_tagref = {
    #       "b15-1": [(
    #           <lxml TextBlockElement>,
    #           {
    #               "Style_1":{
    #                   'open': '<strong><em>',
    #                   'close': '</em></strong>',
    #               }
    #           }
    #       )]
    #   }
    text_blocks_by_tagref = defaultdict(list)
    for alto in case_xml.pages.all():
        parsed_alto_page = parse_xml(alto.orig_xml)

        # Make a dict of page styles and associated casexml tags.
        # Styles that don't call for casexml tags are excluded.
        page_styles = {}
        for style in parsed_alto_page('alto|TextStyle'):
            if style.get("FONTSTYLE"):
                known_styles = sorted(i for i in style.get("FONTSTYLE").split(" ") if i in styles)
                if known_styles:
                    page_styles[style.get("ID")] = {
                        'open': ''.join(styles[i]['open'] for i in known_styles),
                        'close': ''.join(styles[i]['close'] for i in reversed(known_styles)),  # use reverse so tags are properly nested
                    }

        # index text blocks
        for text_block in parsed_alto_page('alto|TextBlock[TAGREFS]'):
            text_blocks_by_tagref[text_block.get('TAGREFS')].append((text_block, page_styles))

    previous_page=None
    # Process each casebody element with a pgmap attribute:
    for casebody_element in parsed_case("casebody|casebody [pgmap]"):

        current_final_page = casebody_element.attrib['pgmap'].split(' ')[-1].split('(')[0]
        if previous_page != current_final_page and ' ' not in casebody_element.attrib['pgmap']:
            first_text_element = True
            previous_page = current_final_page

        if casebody_element.text.isspace():
            continue

        # make a list of each alto string that contributes to the casebody element, in a tuple along with its
        # style (or None, if the alto string is unstyled), and the alto id to check for page breaks.
        # Spaces are removed and soft hyphens are normalized to hard hyphens.
        alto_text_blocks = text_blocks_by_tagref[casebody_element.get('id')]
        alto_strings = [
            (alto_string.get("CONTENT").replace('\xad', '-').replace(' ', ''), page_styles.get(alto_string.get("STYLEREFS"), None), alto_string.get("ID"))
            for text_block, page_styles in alto_text_blocks
            for alto_string in parsed_case(text_block)("alto|String")
        ]

        # the first element of every alto_text_block except the first should be preceded by a page break
        page_breaks = []
        if len(alto_text_blocks) > 1:
            page_breaks = [ parsed_case(text_block)("alto|String")[0].get("ID") for text_block, page_styles in alto_text_blocks if text_block.get("ID").split(".")[1] == '1' ]

        if not any(p[1] for p in alto_strings) and len(page_breaks) == 0:
            continue

        # Create a single string of alto text, as well as a list with the style for each character in the string:
        alto_text = ''.join(i[0] for i in alto_strings)
        alto_styles = [
            (style, alto_info[2])
            for alto_info in alto_strings
            for style in [alto_info[1]]*len(alto_info[0])
        ]

        # Now we have the alto text, we can extract the casebody text and coerce it to match:

        # Extract raw XML from the casebody element:
        casebody_element_text = PyQuery(casebody_element).html()

        # etree.tostring puts in bogus xmlns attributes:
        casebody_element_text = re.sub(r' xmlns(?:\:\w+)?=".*?"', '', casebody_element_text)

        # Extract XML tags and spaces and store them in a separate insertions dictionary:
        casebody_element_text, insertions = split_string_and_insertions(casebody_element_text, r'(<.*?>|\s+)')

        # Decode &amp; to & so it matches the alto text:
        casebody_element_text = html.unescape(casebody_element_text)

        # Normalize soft hyphens to hard hyphens:
        output_text = casebody_element_text
        casebody_element_text = casebody_element_text.replace('\xad', '-')

        # Handle remaining cases where text does not match:
        if casebody_element_text != alto_text:

            if strict:
                raise Exception(
                    "Case text and alto text do not match for case_xml ID %s, element ID %s.\n"
                    "Case text: %s\nAlto text: %s"
                    % (case_xml.pk, casebody_element.get('id'), casebody_element_text, alto_text)
                )

            # To handle mismatches, diff the two strings and patch alto_styles to match casebody_element_text.
            # For example, suppose casebody_element_text = "abXcdef", alto_text = "abcdYef", and
            # alto_styles = [1, 2, 3, 4, 5, 6, 7]. This patches alto_styles to [1, 2, 2, 3, 4, 6, 7],
            # so each letter in casebody_element_text will receive the appropriate style.
            diff = difflib.SequenceMatcher(None, alto_text, casebody_element_text)
            i = 0
            for tag, i1, i2, j1, j2 in diff.get_opcodes():
                if tag == "delete":
                    del alto_styles[i1 + i:i2 + i]
                    i -= i2 - i1
                elif tag == "replace":
                    alto_styles[i1 + i:i2 + i] = [alto_styles[i1+i-1]] * (j2 - j1)
                    i -= i2 - i1 - j2 + j1
                elif tag == "insert":
                    alto_styles[i1 + i:i2 + i] = [alto_styles[i1+i-1]] * (j2 - j1)
                    i += j2 - j1

        # Style each letter in casebody_element_text:
        for cursor, (casebody_char, current_info, previous_info) in enumerate(zip(casebody_element_text, alto_styles, [None]+alto_styles[:-1])):

            # separate styles and alto element names for better code readability
            current_tags = current_info[0] if current_info and current_info[0] else None
            previous_tags = previous_info[0] if previous_info and previous_info[0] else None
            alto_element = current_info[1] if current_info and current_info[1] else None

            # see if the style has changed, and if so, apply the closing tag
            if previous_tags and (not current_tags or current_tags['close'] != previous_tags['close']):
                insertions[cursor].insert(0, previous_tags['close'])

            if current_tags:
                # If tag changes, new style tag needs to be opened:
                if not previous_tags or (current_tags['open'] != previous_tags['open']):
                    insertions[cursor].append(current_tags['open'])

                # If tag does not change, we may need to wrap an existing tag like <footnote> in </em><footnote><em>:
                elif cursor in insertions and not ''.join(insertions[cursor]).isspace():
                    insertions[cursor].append(current_tags['open'])
                    insertions[cursor].insert(0, current_tags['close'])

            # check if this element needs a page break
            if first_text_element:
                first_text_element = False
                page_marker = page_number_html(alto_element, parsed_case)
                insertions[cursor].append(page_marker)

            # check if this element needs an inline page break
            if len(page_breaks) > 0 and alto_element in page_breaks:
                page_marker = page_number_html(alto_element, parsed_case)
                insertions[cursor].append(page_marker)
                page_breaks.remove(alto_element)

        # Add final closing tag:
        if current_tags:
            insertions[cursor+1].insert(0, current_tags['close'])

        # Write text back to parsed xml:
        output_text = join_string_and_insertions(output_text, insertions)
        PyQuery(casebody_element).html(output_text)

    plain_case_text = force_str(serialize_xml(parsed_case))

    # Make sure that we haven't modified the XML outside of the tags:
    new_stripped_xml = re.sub(strip_style_tags_re, '', re.sub(strip_pagebreaks, '', plain_case_text))
    if stripped_xml != new_stripped_xml:
        diff = ''.join(difflib.context_diff(stripped_xml.splitlines(keepends=True), new_stripped_xml.splitlines(keepends=True), n=0))
        raise Exception("Styling XML failed: original text and styled text do not match:\n%s" % diff)

    return plain_case_text

def page_number_html(alto_element, parsed_case):
    sequence_number = alto_element.split('_')[1].split('.')[0]
    printed_page = parsed_case("mets|div[ORDER='{}']".format(sequence_number)).attr('ORDERLABEL')
    # Make this add the page in as an attribute to the tag
    return '<page-number id="p{0}" href="#p{0}" label="{0}" citation-index="1">*{0}</page-number>'.format(printed_page)