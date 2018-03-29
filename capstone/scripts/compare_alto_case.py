from scripts.helpers import parse_xml


def validate(case_xml, consecutive_bad_word_limit=2):
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

    # put in placeholders for the inline tags we want to keep-- this simplifies
    # controlling iteration over the two different sets of XML
    prepared_case = case_xml.orig_xml
    for tag in inline_placeholders:
        prepared_case = prepared_case.replace(tag, inline_placeholders[tag])

    # strip out any existing style tags
    for tag in styles:
        prepared_case = prepared_case.replace(styles[tag]["open"], "").replace(styles[tag]["close"], "")

    parsed_case = parse_xml(prepared_case)

    return_status = {}
    return_status['problems'] = []
    return_status['case'] = case_xml.metadata.case_id

    # dup cases have no casebody to style
    if parsed_case('duplicative|casebody'):
        return_status['status'] = 'ok'
        return_status['results'] = 'duplicative'
        return return_status

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

        # loop through each alto page referenced in the pagemap of the casexml element
        for alto in element_pages:

            parsed_alto_page = alto_files[alto]
            text_block = parsed_alto_page(
                'alto|TextBlock[TAGREFS="{}"]'.format(casebody_element.get('id')))

            consecutive_bad_words = 0
            # loop through each alto String for each page
            for alto_string in text_block("alto|String"):
                # skip spaces
                if casebody_element_text[0] == ' ':
                    casebody_element_text = casebody_element_text[1:]

                bad_word_flag = False
                # loop through each character of the string
                for i in range(0, len(alto_string.get("CONTENT"))):

                    # is this the start of a tag?
                    if casebody_element_text.startswith('__TAG_'):

                        # move the tag text from casebody_element_text to new
                        casebody_element_text = casebody_element_text[28:]

                        # move any spaces
                        if casebody_element_text[0] == ' ':
                            casebody_element_text = casebody_element_text[1:]

                        # now deal with the character we're iterating over
                        if casebody_element_text[0] == alto_string.get("CONTENT")[i]:
                            casebody_element_text = casebody_element_text[1:]
                    # do the chars match, or are they both different dashes?
                    elif casebody_element_text[0] == alto_string.get("CONTENT")[i] or \
                            (casebody_element_text[0] == '\xad' and alto_string.get("CONTENT")[i] == '-'):

                        # and remove the character from casebody_element_text
                        casebody_element_text = casebody_element_text[1:]
                    else:
                        # these are some methods to deal with extra characters
                        # either in ALTO text, or CaseMETS. If we decided that
                        # these sorts of discrepancies were ok, this logic
                        # could be expanded pretty easily.

                        alto_context = {}
                        casemets_context= {}
                        problem_guess = None

                        alto_context["prev"] = None
                        alto_context["current"] = { alto_string.get('ID'): alto_string.get('CONTENT') }
                        alto_context["current_character"] = { alto_string.get('ID'): alto_string.get('CONTENT')[i] }
                        alto_context["next"] = None

                        snippet_beginning = len(casebody_element.text) - len(casebody_element_text) - 20 if len(casebody_element.text) - len(casebody_element_text) >= 20 else 0
                        snippet_end = len(casebody_element.text) - len( casebody_element_text) + 20

                        casemets_context["snippet"] = casebody_element.text[snippet_beginning:snippet_end]
                        casemets_context["current"] = casebody_element_text[:len(alto_string.get('CONTENT'))]
                        casemets_context["current_character"] = casebody_element_text[0]

                        # This code deals with cases where there is an extra
                        # character in an alto representation of a string. For
                        # example, in 32044057892259_00001, the end of the
                        # string "24 Ill. 113;" is incorrectly represented
                        # in alto as "113­" and ";"
                        if alto_string.getnext() is not None:
                            if alto_string.getnext().get('CONTENT') is not None:
                                alto_context["next"] = {alto_string.getnext().get('ID'): alto_string.getnext().get('CONTENT')}

                            if alto_context["next"] is None and alto_string.getnext().getnext() is not None:
                                if alto_string.getnext().getnext().get('CONTENT') is not None:
                                    alto_context["next"] = {
                                        alto_string.getnext().getnext().get('ID'): alto_string.getnext().getnext().get(
                                            'CONTENT')}

                        if alto_string.getprevious() is not None:
                            if alto_string.getprevious().get('CONTENT') is not None:
                                alto_context["prev"] = {alto_string.getprevious().get('ID'): alto_string.getprevious().get('CONTENT')}

                            if alto_context["prev"] is None and alto_string.getprevious().getprevious() is not None:
                                if alto_string.getprevious().getprevious().get('CONTENT') is not None:
                                    alto_context["prev"] = {
                                        alto_string.getprevious().getprevious().get('ID'): alto_string.getprevious().getprevious().get(
                                            'CONTENT')}
                        # this checks the next alto element for a match:
                        if problem_guess is None and alto_string.getnext() is not None:
                            if alto_string.getnext().getnext() is not None:
                                if casebody_element_text.startswith(alto_string.getnext().getnext().get("CONTENT")):
                                    problem_guess = "extra char in alto? match found subsequent alto element"
                        # this checks the current element:
                        if problem_guess is None and len(alto_string.get("CONTENT")) > i + 1:
                            if alto_string.get("CONTENT")[i + 1:].startswith(
                                    casebody_element_text[0:len(alto_string.get("CONTENT")) - i]):
                                    problem_guess = "extra char in alto? match found in current alto element"

                        # this checks for an extra character in the caseMETS
                        # For example, in 32044057892259_00001 in <p id="Ad5">
                        # the string "subject-­matter" is represented in the
                        # ALTO as "subject-" and "matter"
                        if problem_guess is None and casebody_element_text[1:].startswith(alto_string.get("CONTENT")):
                            problem_guess = "extra char in case_mets? match found in current alto"
                            casebody_element_text = casebody_element_text[2:]


                        if problem_guess is None:
                            problem_guess = "Unspecified Mismatch."

                        if not bad_word_flag:
                            from pprint import pprint
                            pprint({"description": problem_guess, "alto": alto_context, "casemets": casemets_context})
                            return_status['problems'].append({"description": problem_guess, "alto": alto_context, "casemets": casemets_context})
                            bad_word_flag = True
                            consecutive_bad_words += 1
                            if consecutive_bad_words >= consecutive_bad_word_limit:
                                return_status['status'] = "error"
                                return_status['results'] = 'gave up after {} consecutive bad words'.format(consecutive_bad_words)
                                return return_status

                #reset the consecutive counter for good words
                if not bad_word_flag:
                    consecutive_bad_words = 0



        # the casebody_element_text should contain no characters unless
        # it is a closing tag, or trailing spaces for formatting
        if len(casebody_element_text) > 0:
            if casebody_element_text.startswith('__TAG_'):
                casebody_element_text = casebody_element_text[28:]
            if casebody_element_text.isspace():
                pass
            elif len(casebody_element_text) > 0:
                return_status['problems'].append(
                    {"description": "Leftover chars in casebody element not found in ALTO", "casemets": casebody_element_text})

    if len(return_status['problems']) > 0:
        return_status['status'] = 'warning'
        return_status['results'] = 'encountered {} problems'.format(len(return_status['problems']))
    else:
        return_status['status'] = 'ok'
        return_status['results'] = 'clean'

    return return_status


