from scripts.helpers import parse_xml


def generate_styled_case_xml(case_xml, strict=True):
    # Dealing with inline tags as elements ramps up the complexity of this
    # algorithm considerably. I'm replacing inline tags with placeholders
    # while mapping to the alto text, and replacing them with tags after
    # the XML has been serialized at the end.
    # If the citation tag ends up having some sort of attributes,
    # this script will need to be changed to use regex instead of a blanket
    # .replace() and probably store individual tags with their attributes
    # in a dictionary to be retrieved later. This is more efficient.

    # these are the styles we're interested in taking from ALTO, and what
    # we want their placeholders to be
    styles = {}
    styles['bold'] = {}
    styles['italics'] = {}
    styles['bold']['open'] = "__TAG_STN_OPEN_REPLACEMENT__"
    styles['bold']['close'] = "__TAG_STN_CLOS_REPLACEMENT__"
    styles['italics']['open'] = "__TAG_EMP_OPEN_REPLACEMENT__"
    styles['italics']['close'] = "__TAG_EMP_CLOS_REPLACEMENT__"

    # this is what we want the existing tags to be replaced with
    # during processing
    inline_placeholders = {
        "<inlinecitation>": "__TAG_ILC_OPEN_REPLACEMENT__",
        "</inlinecitation>": "__TAG_ILC_CLOS_REPLACEMENT__",
        "<footnotemark>": "__TAG_FNM_OPEN_REPLACEMENT__",
        "</footnotemark>": "__TAG_FNM_CLOS_REPLACEMENT__",
        "<bracketnum>": "__TAG_BKN_OPEN_REPLACEMENT__",
        "</bracketnum>": "__TAG_BKN_CLOS_REPLACEMENT__",
        "<strong>": "__TAG_STN_OPEN_REPLACEMENT__",
        "</strong>": "__TAG_STN_CLOS_REPLACEMENT__",
        "<em>": "__TAG_EMP_OPEN_REPLACEMENT__",
        "</em>": "__TAG_EMP_CLOS_REPLACEMENT__"
    }

    # just the inverse of inline_placeholders. it's easier to replace the tags this way
    inline_tags = {inline_placeholders[key]: key for key in inline_placeholders}

    # put in placeholders for the inline tags we want to keep-- this simplifies
    # controlling iteration over the two different sets of XML
    prepared_case = case_xml.orig_xml
    for tag in inline_placeholders:
        prepared_case = prepared_case.replace(tag, inline_placeholders[tag])

    # strip out any existing style tags
    for tag in styles:
        prepared_case = prepared_case.replace(styles[tag]["open"], "").replace(styles[tag]["close"], "")

    parsed_case = parse_xml(prepared_case)

    # dup cases have no casebody to style
    if parsed_case('duplicative|casebody'):
        raise Exception("Duplicative case: no casebody data to merge")

    casebody_tree = parsed_case("casebody|casebody")[0]

    # get the alto files associated with the case in the DB
    alto_files = {}
    for alto in case_xml.pages.all():
        alto_fileid = "_".join((["alto"] + alto.barcode.split('_')[1:3]))
        alto_files[alto_fileid] = parse_xml(alto.orig_xml)

    # The strategy here is to loop over each casebody element, then each alto
    # page associated with each element, then each String in the alto file,
    # then each character in the word. There are too many exceptions simply
    # trying to split the casebody up by space and match to the alto words.
    for casebody_element in casebody_tree.iter():
        # the casebody and opinion elements contain no stylable text, directly
        if casebody_element.tag.endswith("casebody") or \
                casebody_element.tag.endswith("opinion") or \
                casebody_element.text.isspace():
            continue

        # in the alto_connections dict is a map between the pgmap value, such as '17' and the
        # FILEID value, such as alto_0008_0
        alto_connections = {}
        alto_element_references = parsed_case(
            'mets|area[BEGIN="{}"]'.format(casebody_element.get('id'))).parent().nextAll('mets|fptr')
        for area in alto_element_references('mets|area'):
            pgmap = area.get('BEGIN').split(".")[0].split("_")[1]
            alto_connections[pgmap] = area.get('FILEID')

        # frequently, case text elements span pages. This gets the alto pages referred
        # to by the element's pagemap attribute, and returns the alto_id of the page
        if "pgmap" in casebody_element.keys() and ' ' in casebody_element.get("pgmap"):
            element_pages = [alto_connections[page.split('(')[0]] for page in
                             casebody_element.get("pgmap").split(" ")]
        elif "pgmap" in casebody_element.keys():
            element_pages = [alto_connections[casebody_element.get("pgmap")]]

        casebody_element_text = casebody_element.text
        new_casebody_element_text = ''

        # loop through each alto page referenced in the pagemap of the casexml element
        for alto in element_pages:
            current_style = None

            parsed_alto_page = alto_files[alto]
            text_block = parsed_alto_page(
                'alto|TextBlock[TAGREFS="{}"]'.format(casebody_element.get('id')))

            # make a dict of ALTO page styles which modify the font style
            page_styles = {}
            for style in parsed_alto_page('alto|TextStyle'):
                if style.get("FONTSTYLE") is not None:
                    for fontstyle in sorted(style.get("FONTSTYLE").split(" ")):
                        page_styles[style.get("ID")] = {}
                        page_styles[style.get("ID")]['open'] = ''
                        page_styles[style.get("ID")]['close'] = ''
                        if fontstyle in styles:
                            page_styles[style.get("ID")]['open'] = styles[fontstyle]['open'] + \
                                                                   page_styles[style.get("ID")]['open']
                            page_styles[style.get("ID")]['close'] = page_styles[style.get("ID")]['close'] + \
                                                                    styles[fontstyle]['close']

            # loop through each alto String for each page
            for alto_string in text_block("alto|String"):
                # see if the style has changed, and if so, apply the closing tag placeholder
                if current_style is not None and current_style in page_styles:
                    if alto_string.get("STYLEREFS") not in page_styles or \
                            page_styles[alto_string.get("STYLEREFS")]['close'] != page_styles[current_style]['close']:
                        new_casebody_element_text += page_styles[current_style]['close']

                # skip spaces
                if casebody_element_text[0] == ' ':
                    new_casebody_element_text += ' '
                    casebody_element_text = casebody_element_text[1:]

                # see if a new style tag needs to be opened
                if alto_string.get("STYLEREFS") in page_styles and \
                        alto_string.get("STYLEREFS") != current_style:
                    new_casebody_element_text += page_styles[alto_string.get("STYLEREFS")]['open']

                current_style = alto_string.get("STYLEREFS")

                # loop through each character of the string
                for i in range(0, len(alto_string.get("CONTENT"))):

                    # is this the start of a tag?
                    if casebody_element_text.startswith('__TAG_'):
                        # close out the style tag before starting a new tag.
                        if current_style in page_styles:
                            new_casebody_element_text += page_styles[current_style]['close']

                        # move the tag text from casebody_element_text to new
                        new_casebody_element_text += casebody_element_text[0:28]
                        casebody_element_text = casebody_element_text[28:]

                        # move any spaces
                        if casebody_element_text[0] == ' ':
                            new_casebody_element_text += ' '
                            casebody_element_text = casebody_element_text[1:]

                        # re-open any style tags
                        if current_style in page_styles:
                            new_casebody_element_text += page_styles[current_style]['open']

                        # now deal with the character we're iterating over
                        if casebody_element_text[0] == alto_string.get("CONTENT")[i]:
                            new_casebody_element_text += casebody_element_text[0]
                            casebody_element_text = casebody_element_text[1:]
                    # do the chars match, or are they both different dashes?
                    elif casebody_element_text[0] == alto_string.get("CONTENT")[i] or \
                            (casebody_element_text[0] == '\xad' and alto_string.get("CONTENT")[i] == '-'):

                        # add the character on to the new_casebody_element_text
                        new_casebody_element_text += casebody_element_text[0]
                        # and remove the character from casebody_element_text
                        casebody_element_text = casebody_element_text[1:]
                    elif strict is False:
                        # these are some methods to deal with extra characters
                        # either in ALTO text, or CaseMETS. If we decided that
                        # these sorts of discrepancies were ok, this logic
                        # could be expanded pretty easily.

                        # This code deals with cases where there is an extra
                        # character in an alto representation of a string. For
                        # example, in 32044057892259_00001, the end of the
                        # string "24 Ill. 113;" is incorrectly represented
                        # in alto as "113­" and ";"

                        # this checks the next alto element for a match:
                        if alto_string.getnext() is not None:
                            if alto_string.getnext().getnext() is not None:
                                if casebody_element_text.startswith(alto_string.getnext().getnext().get("CONTENT")):
                                    continue
                        # this checks the current element:
                        elif len(alto_string.get("CONTENT")) > i + 1:
                            if alto_string.get("CONTENT")[i + 1:].startswith(
                                    casebody_element_text[0:len(alto_string.get("CONTENT")) - i]):
                                continue

                        # this checks for an extra character in the caseMETS
                        # For example, in 32044057892259_00001 in <p id="Ad5">
                        # the string "subject-­matter" is represented in the
                        # ALTO as "subject-" and "matter"
                        if casebody_element_text[1:].startswith(alto_string.get("CONTENT")):
                            new_casebody_element_text += casebody_element_text[0:2]
                            casebody_element_text = casebody_element_text[2:]
                            continue

                        # if none of that manages to solve it, we'll throw
                        # even if strict is False
                        raise Exception(
                            "Unrecoverable character discrepency in ALTO (\"{}\") and CaseMETS (\"{}\")".format(
                                alto_string.get("CONTENT")[i:],
                                casebody_element_text[:len(alto_string.get("CONTENT")[i:])]))
                    else:
                        raise Exception("Character discrepency between ALTO (\"{}\") and CaseMETS (\"{}\")".format(
                            alto_string.get("CONTENT")[i:],
                            casebody_element_text[:len(alto_string.get("CONTENT")[i:])]))

            # if new casebody deosn't end with closing tag, add it
            # because it won't loop through again to add it above
            if current_style in page_styles and \
                    not new_casebody_element_text[28:].endswith(page_styles[alto_string.get("STYLEREFS")]['close']) and \
                    not new_casebody_element_text.endswith(page_styles[alto_string.get("STYLEREFS")]['close']):
                new_casebody_element_text += page_styles[current_style]['close']

        # the casebody_element_text should contain no characters unless
        # it is a closing tag, or trailing spaces for formatting
        if len(casebody_element_text) > 0:
            if casebody_element_text.startswith('__TAG_'):
                new_casebody_element_text += casebody_element_text[0:28]
                casebody_element_text = casebody_element_text[28:]
            if casebody_element_text.isspace():
                new_casebody_element_text += casebody_element_text
            elif len(casebody_element_text) > 0:
                raise Exception(
                    "Trailing characters on casebody element which didn't seem to be\
                     in the ALTO text. This indicates unclean CaseXML/Alto match-up.\
                      These are the leftover characters: '{}'".format(
                        casebody_element_text))

        casebody_element.text = new_casebody_element_text
    plain_case_text = str(parsed_case)

    # replace the placeholders with their tags!
    for placeholder in inline_tags:
        plain_case_text = plain_case_text.replace(placeholder, inline_tags[placeholder])

    return plain_case_text

