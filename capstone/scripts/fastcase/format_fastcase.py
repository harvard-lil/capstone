import subprocess
from copy import deepcopy
from html import unescape, escape
import regex as re
from lxml import etree
from pyquery import PyQuery

from scripts.extract_cites import extract_citations_from_text
from scripts.helpers import inner_html, alphanum_lower
from scripts.render_case import remove_empty_tags, VolumeRenderer

"""
    This file converts Fastcase HTML to CAP HTML and XML. This is a heuristic process involving fixing various HTML
    formatting issues and guessing which parts of the case are which.
    
    The main entry point is format_fastcase_html(), which takes a CAP case with case.fastcase_import populated and
    returns the HTML and XML. The file also offers format_fastcase_html_from_parts() to support the dump_html()
    command in ingest_fastcase.py.
    
    File organization:
    
    * stuff used by the pipeline functions:
        * regex helpers
        * data helpers
        * function helpers
    * pipeline functions -- each step of converting input html to output html
    * entry points -- top-level functions that call the pipeline functions
"""


## regex helpers ##

# a string ending with this re was likely split mid-sentence and should be joined with the following paragraph
mid_sentence_re = re.compile(r'''
    (?: 
        # whole words
        \ (?:
            # abbreviations
            (?:Dr|Mr|Mrs|Ms)\.|
            # single-letter words starting sentences
            [AI]
        )|
        # lowercase letters and mid-sentence punctuation
        [a-z0-9,\-\(]
    )$
''', flags=re.VERBOSE)


# match each <br><br> and each <p> or <blockquote>, so we can replace each <br><br>
# with the most recent block element
double_br_re = re.compile(r'''
    (?P<double_br><br>\s*<br>)|
    <(?P<last_tag>p|blockquote)>
''', flags=re.VERBOSE | re.DOTALL)


# match a short or long month
months_re = r'''
    (?:
        January|February|March|April|May|June|July|August|September|October|November|December|
        Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec
    )
'''

# match a date
date_re = re.compile(rf'''
        # June 12, 2001
        {months_re}
        \.?\ ?
        \d{{1,2}}
        ,?\ ?
        (?:19|20)\d\d
    |
        # 12 June 2001
        \d{{1,2}}
        \ {months_re}
        ,?\ ?
        (?:19|20)\d\d
''', flags=re.VERBOSE | re.I)


# match strings that are plausible citations
citation_like_re = re.compile(r'''
    ^
    (?:\d+|_+)  # volume
    \ (?:[a-zA-Z0-9\.]+){1,3}  # up to three words of reporter
    \ (?:\d+|_+)  # page
    $
''', flags=re.VERBOSE | re.I)


## data helpers ##
# (lists of strings or situations we need to look for when processing cases line by line)

# detecting splits between majority and dissenting opinions
# From https://github.com/harvard-lil/CaselawAccessProjectSchemas/blob/master/casebodyxml/v1/casebodyxml.xsd ,
# opinion type can be one of
# [ "majority", "unanimous", "plurality", "concurrence", "dissent", "remittitur", "rehearing", "on-the-merits",
#   "on-motion-to-strike-cost-bill", "concurring-in-part-and-dissenting-in-part"]
opinion_type_lookup = {
    "concurring in part and dissenting in part": "concurring-in-part-and-dissenting-in-part",
    "dissenting": "dissent",
    "concurring": "concurrence",
}
# "ANN WALSH BRADLEY, J. (dissenting)."
new_opinion_re = re.compile(r'[A-Za-z.,\- ]{,30} \(?(' + '|'.join(re.escape(k) for k in opinion_type_lookup) + r')\)?[.:]?$', flags=re.I)

# detecting start of opinion text and end of head matter
opinion_start_lines = {alphanum_lower(s) for s in (
    "AMENDED OPINION AND ORDER",
    "BY ORDER OF THE COURT",
    "DECISION WITHOUT PUBLISHED OPINION",
    "MEMORANDUM AND ORDER",
    "MEMORANDUM AND ORDER PURSUANT TO RULE 1:28",
    "MEMORANDUM DECISION AND ORDER",
    "MEMORANDUM DECISION AND ORDER DENYING MOTIONS TO TRANSFER VENUE",
    "MEMORANDUM OPINION AND ORDER",
    "MOTION AND PROCEDURAL RULINGS",
    "ON RECONSIDERATION",
    "ON REMAND",
    "OPINION",
    "OPINION AND DISSENT",
    "Opinion of the Court",
    "Order",
    "SPECIAL TERM OPINION",
    "SUPPLEMENTAL OPINION",
    "UPON REHEARING EN BANC",
    "Upon a Petition for Rehearing En Banc",
)}
opinion_start_line_prefixes = {alphanum_lower(s) for s in (
    "ORDERED that",
    "ORDER OF",
    "OPINION AND ORDER",
)}

# detecting judge names
judge_titles = [
    s.lower()
    for s in
    (", J.", ", C.J.", ", P.J.", ", J.A.D.", ", P. J", ", JJ.", ", S.J.", ", A.J.", ", Acting P.J.", "Justice", "Judge",
     ", CHIEF JUDGE", ", Acting P. J.", ", U.S.D.J.", ", UNITED STATES CIRCUIT JUDGE", ", UNITED STATES DISTRICT JUDGE",
     ", Chair", ", Chief U.S. District Court Judge", "MAGISTRATE JUDGE", ", UNITED STATES BANKRUPTCY JUDGE")
]


## function helpers ##

# provides helper functions for making CAP html parts
renderer = VolumeRenderer(format='html', pretty_print=False)


def make_page_label(label, index=1):
    """
        Make HTML for a page label:

        >>> make_page_label('123', 2)
        '<a id="p123" href="#p123" data-label="123" data-citation-index="2" class="page-label">**123</a>'
    """
    return etree.tostring(renderer.render_sax_tags(renderer.page_label_tags(label, index)), encoding=str,
                          method='html')


def strip_tags(line):
    """
        Remove <sup> and <a> tags and their contents, as well as other tags without removing their contents.

        >>> strip_tags('foo <a href="">bar</a><sup>1</sup> <i>baz</i>')
        'foo  baz'
    """
    return re.sub(r'<sup[^>]*>.*?</sup>|<a[^>]*>.*?</a>|<[^>]+>', '', unescape(line), flags=re.S)


def similar_strings(s1, s2):
    """
        Return true if at least half of the words in s1 are also in s2.

        >>> assert similar_strings('1 2 3', '2 1 4')
        >>> assert not similar_strings('1 2 3', '5 1 4')
    """
    w1 = set(re.split(r'\W+', s1))
    w2 = set(re.split(r'\W+', s2))
    threshold = len(w1) // 2 + 1
    return len(w1 & w2) >= threshold


def wrap_with(old_el, new_el):
    """Wrap PyQuery element `old_el` with PyQuery element `new_el`."""
    new_el.insert_before(old_el)
    new_el.append(old_el)
    return new_el


def is_judges_or_author(line_text):
    """
        Return True if line appears to be the name of a judge or judges, based on a series of heuristics.
    """
    # line can't be too long
    if len(line_text) > 80:
        return False

    line_lower = line_text.lower()

    # 'Before DYKMAN, VERGERONT and LUNDSTEN, JJ.'
    # 'Present: All the Justices.'
    if any(line_lower.startswith(s) for s in ("before", "present", "considered and decided by")) or 'en banc' in line_lower:
        return "judges"

    # 'PER CURIAM.'
    if any(s in line_lower for s in ('per curiam', 'opinion by', 'by the court')):
        return "author"

    if any(s in line_lower for s in judge_titles):
        if " and " in line_text or " & " in line_text:
            return "judges"
        else:
            return "author"

    return None


def reindent(el, indent=2, depth=0):
    r"""
        Reindent lxml element el, but only for elements that already have a linebreak before them.
        This lets us get nicely formatted HTML by making sure there's a linebreak before each element we want indented.

        >>> tree=etree.fromstring('<a>\n<b>\n<c><d></d></c>\n</b>\n</a>')
        >>> reindent(tree)
        >>> etree.tostring(tree, encoding=str)
        '<a>\n  <b>\n    <c><d/></c>\n  </b>\n</a>'
    """
    depth += 1
    indent_str = ' '*depth*indent
    if el.text and el.text.startswith('\n'):
        el.text = '\n' + indent_str + el.text.lstrip()
    last_child_index = len(el) - 1
    for i, child in enumerate(el):
        reindent(child, indent, depth)
        if child.tail and child.tail.startswith('\n'):
            child.tail = '\n' + (indent_str[:-indent] if i == last_child_index else indent_str) + child.tail.lstrip()


## processing pipeline ##
# each step called by format_fastcase_html_from_parts, in order

def prepare_html_for_tidy(fastcase_data):
    """
        Combine HeaderHtml and CaseHtml from fastcase_data, and apply initial regex fixups.
    """
    # strip formatting tags from header -- these are replaced by our styling of header elements
    header_html = re.sub(r'</?(b|strong|em|span[^>]*)>', '', fastcase_data['HeaderHtml'], flags=re.I)

    html = header_html + '<header-end/>' + fastcase_data['CaseHtml']

    # replace <center> with <p>
    html = re.sub(r'<(/?)center>', r'<\1p>', html, flags=re.I)

    # remove small tags -- unneeded when wrapping footnote numbers, and invalid when wrapping entire notes section
    # remove empty <a> tags -- SE2d/590/590SE2d792_GA_Pag.xml
    html = re.sub(r'</?small>|<a>', '', html, flags=re.I)

    # convert double <br> to paragraph break
    # keep track of previously entered tag so we know what to close and reopen in place of <br><br>
    last_tag = None
    def fix_double_br(m):
        nonlocal last_tag
        if m['double_br'] and last_tag:
            return f'</{last_tag}>\n  <{last_tag}>'
        if m['last_tag']:
            last_tag = m['last_tag']
        return m[0]
    html = double_br_re.sub(fix_double_br, html)

    # escape angle brackets around links, like <html://example.com> -- e.g. CalRptr3d/217/217 Cal.Rptr.3d 704.xml
    html = re.sub(r'<(\s*http[^>]+)>', r'&lt;\1&gt;', html)

    # fix dollar signs written as '<gtdollargt>', like SE2d/592/592SE2d124_GA_Pag.xml
    html = html.replace('<gtdollargt>', '$')

    return html


def html_tidy(html, **kwargs):
    """
        Call the `tidy` command as a subprocess with the given html and flags.
        If tidy objects to any unrecognized tags, escape them and include in the returned warnings list.
    """
    tidy_flags = {
        'quiet': 'yes',
        'show_warnings': 'no',
        'enclose_text': 'yes',  # add <p> around bare text. don't want --enclose-block-text because it puts <p> inside <blockquote>
        'show_body_only': 'yes',  # don't add an html document
        'bare': 'yes',  # convert &nbsp; to space
        'logical_emphasis': 'yes',  # convert i to em
        'new_blocklevel_tags': 'header-end',  # allow our custom tags
        'wrap': '0',  # don't line wrap
        'hide_comments': 'yes',  # remove comments
        'indent': 'yes',
        **kwargs,
    }
    warnings = []
    tidy_flags_as_params = [i for k, v in tidy_flags.items() for i in ('--'+k.replace('_', '-'), v)]
    while True:
        result = subprocess.run(
            ['tidy'] + tidy_flags_as_params,
            input=html,
            encoding="utf8",
            capture_output=True)

        # check for error -- tidy uses exit code 1 for warnings
        if result.returncode > 1:
            # attempt to recover from unrecognized tag by escaping tag
            m = re.search(r'<(\w+)> is not recognized', result.stderr)
            if m:
                new_html = html.replace('<'+m[1], '&lt;'+m[1])
                if new_html != html:
                    warnings.append(f"Escaped unrecognized tag {repr(m[1])}")
                    html = new_html
                    continue
            raise ValueError(f"tidy command failed: {result.stderr}")
        break
    return result.stdout, warnings


def post_tidy_html_fixes(html):
    # fix spaces after closing italics? need to document this more
    # html = re.sub(r'(</i>) ([,’])', r'\1\2', html)

    # should <i>, <b>, and <u> all become <em> ?
    html = re.sub(r'<(/?)[iu]>', r'<\1em>', html)
    html = re.sub(r'<(/?)[b]>', r'<\1strong>', html)

    return html


def segment_paragraphs(root_el, cites=[]):
    """
        Replace Fastcase page numbers like "[935 F.3d 745]" or "Page 745" with CAP page numbers like
            <a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a>.

        Also clean whitespace, remove empty paragraphs, and merge paragraphs split by page numbers.
    """
    from capdb.models import Citation

    last_el_ends_mid_sentence = False
    join_with_last_el = False
    html_to_prepend_to_next_el = ''

    # build a lookup like {"935 F.3d": 1, "123 Mass.": 2}
    reporter_indexes = {}
    for i, cite in enumerate(Citation.sorted_by_type(cites)):
        eyecite_cite = next(extract_citations_from_text(cite.cite), None)
        if eyecite_cite:
            volume = eyecite_cite.groups['volume']
            reporter = eyecite_cite.groups['reporter']
            reporter_indexes[f"{volume} {reporter}"] = i+1

            # special case -- "[134 Hawai'i 89]" is a page number for "134 Haw. 86"
            if reporter == 'Haw.':
                reporter_indexes[f"{volume} Hawai'i"] = i + 1

    # process each paragraph
    for el_pq in PyQuery(root_el)('root').children().items():
        el = el_pq[0]
        if el.tag == 'header-end':
            continue

        html = inner_html(el)
        page_label = None
        exact_match = False
        index = 1

        # clean el whitespace
        clean_html = re.sub(r'\s+|^<br>|<br>$', ' ', html).strip()
        if not clean_html:
            el_pq.remove()
            continue

        # strip tags to handle examples like
        # "<p><strong>[16 N.Y.3d 274] <strong> <p/></strong></strong> <p> <strong> [945 N.E.2d 484]</strong> </p> <p> <strong>OPINION OF THE COURT</strong> </p></p>"
        # in NE2d/945/945ne2d484.xml
        html_no_tags = strip_tags(clean_html).strip()

        # check for 'Page 123'
        m = re.match(r'Page (\d+)$', html_no_tags)
        if m:
            page_label = make_page_label(m[1])
            exact_match = True

        # check for '[123 Mass. 456]'
        else:
            m = re.search(r"\[(?P<volume>\d+) (?P<reporter>[A-Z][A-Za-z0-9 .']+) (?P<page>\d+)\]", html_no_tags)
            if m:
                vol_reporter = f"{m['volume']} {m['reporter']}"
                if vol_reporter in reporter_indexes:
                    index = reporter_indexes[vol_reporter]
                    is_valid_reporter = True
                else:
                    is_valid_reporter = False
                exact_match = m[0] == html_no_tags
                if exact_match or is_valid_reporter:
                    page_label = make_page_label(m['page'], index)

        # handle page label found
        if page_label:
            clean_html = clean_html.replace(escape(m[0]), page_label)

            if exact_match:
                if last_el_ends_mid_sentence:
                    join_with_last_el = True
                html_to_prepend_to_next_el += clean_html
                el_pq.remove()
                continue

        if html_to_prepend_to_next_el:
            clean_html = html_to_prepend_to_next_el + clean_html
            html_to_prepend_to_next_el = ''

        if join_with_last_el:
            join_with_last_el = False
            prev_el = el_pq.prev()
            if prev_el[0].tag == el_pq[0].tag:
                prev_el.append(('' if prev_el.text().endswith('-') else ' ')+clean_html)
                el_pq.remove()
                continue

        last_el_ends_mid_sentence = bool(mid_sentence_re.search(html_no_tags))

        if clean_html != html:
            el_pq.html(clean_html)


def label_paragraphs(root_el, fastcase_data):
    """
        Step through each paragraph of case, and heuristically attempt to label it as parties, docketnumber,
        decisiondate, author, etc. Also heuristically attempt to split paragraphs between head matter and each
        opinion. Return [header_elements, [opinion_elements, opinion_elements...]]

        This function is full of heuristics and will need to change over time. We can collect test cases in
        test_data/fastcase and use test_fastcase_ingest to measure regressions.
    """
    # case metadata
    citations = [alphanum_lower(" ".join((c["Volume"], c["Reporter"], c["Page"]) + ((c["Suffix"],) if "Suffix" in c else ()))) for c in fastcase_data['Citations']]
    name_clean = alphanum_lower(fastcase_data['PartyHeader']) if fastcase_data['PartyHeader'] else None
    court_clean = alphanum_lower(fastcase_data['CourtName'] or fastcase_data['CourtAbbreviation'])
    docket_numbers_clean = [alphanum_lower(d) for d in fastcase_data['DocketNumbers']]

    # via https://github.com/harvard-lil/CaselawAccessProjectSchemas/blob/master/casebodyxml/v1/casebodyxml.xsd
    states = {k:i for i, k in enumerate([None, "citation", "parties", "docketnumber", "court", "otherdate", "decisiondate", "history", "syllabus", "attorneys", "judges", "disposition", "_opinionstart", "_preauthor", "author", "opinion"])}
    reverse_states = {v:k for k, v in states.items()}

    state = 0
    header_els = []
    opinions = [[]]
    header_complete = False
    extra_els = []
    blank_els = []
    authors = []
    opinion_starts = []
    paragraph_id = 1

    def shift_to_opinion(i):
        """Move i elements from the end of header to the start of opinion."""
        if not i:
            return
        nonlocal header_els
        opinions[0][0:0] = header_els[-i:]
        header_els = header_els[:-i]

    def add_el(el, state, target_list=header_els):
        nonlocal blank_els, paragraph_id
        if state:
            if not reverse_states[state].startswith('_'):
                el.attrib['class'] = reverse_states[state]
            if state == states['_opinionstart']:
                opinion_starts.append((len(target_list), el))
            elif state == states['author']:
                authors.append((len(target_list), el))
            blank_els = []
        else:
            blank_els.append(el)
        el.attrib['id'] = f'p-{paragraph_id}'
        paragraph_id += 1
        target_list.append(el)

    def append_to_previous(line):
        PyQuery(header_els[-1]).append(PyQuery(line))

    for el_pq in PyQuery(root_el)('root').children().items():

        if extra_els:
            extra_els.append(el_pq)
            el_pq = extra_els.pop(0)

        el = el_pq[0]

        # mark the end of the labeled front matter (which may or may not align with actual end)
        if el.tag == 'header-end':
            header_complete = True
            if state == states["author"]:
                state = states["opinion"]
            continue

        # skip
        if el.text == "COPYRIGHT MATERIAL OMITTED":
            continue

        # add linebreak after element for indentation
        if not (el.tail and el.tail.startswith('\n')):
            el.tail = '\n' + (el.tail or '')

        line = inner_html(el)
        line_text = strip_tags(line)
        line_text_lower = line_text.lower()
        line_alphanum_chars = alphanum_lower(line_text)

        # if we've had 5 regular paragraphs in a row, assume we missed the start of the opinion
        if state < states["opinion"] and len(blank_els) >= 5:
            shift_to_opinion(len(blank_els))
            state = states["opinion"]

        # we have now reached the opinion and no longer have to process header lines
        if state >= states["opinion"]:
            # check short lines for the start of a concurrence or dissent
            m = new_opinion_re.match(line_text)
            if m:
                el.attrib['class'] = 'author'
                el.attrib['opinion-type'] = opinion_type_lookup[m[1].lower()]
                opinions.append([])

            add_el(el, 0, opinions[-1])
            continue

        # citation
        if state <= states["citation"]:
            if any(c in line_alphanum_chars for c in citations) or all(citation_like_re.match(s) for s in line.split('<br>')):
                state = states["citation"]
                continue  # don't include citation lines in output

        # parties
        if state < states["parties"]:
            # special case -- if the case doesn't have a name, like NE2d/939/939ne2d586.xml,
            # assume that whatever comes after the last citation is the name
            if name_clean is None or line_alphanum_chars == name_clean:
                state = states["parties"]
                add_el(el, state)
            elif header_els and name_clean == alphanum_lower(inner_html(header_els[-1][0]) + line):
                # handle edge case where name is split across two paragraphs
                append_to_previous(line)
            elif line_alphanum_chars.startswith(name_clean) or similar_strings(line_text, fastcase_data['PartyHeader']):
                # special cases -- NW2d/881/881 N.W.2d 813-4_Replace.xml, NW2d/792/792NW2d203.xml
                state = states["parties"]
                add_el(el, state)
            else:
                # if we haven't found a valid name yet, paragraphs are just regular paragraphs
                add_el(el, 0)
            continue

        # docket numbers or court
        if state < states["court"]:
            # detect 'Supreme Judicial Court of Massachusetts.' and 'United States Bankruptcy Appellate Panel of the Ninth Circuit.' as a court, but not
            # 'Court of Appeals Case No. 04A03-1707-IF-1724' or 'Consol. Court No. 16-00054'
            # line may be 'Court of Appeals of Virginia, Chesapeake.' if court is 'Court of Appeals of Virginia'
            # line may be 'North Carolina Court of Appeals.' if court is 'Court of Appeals of North Carolina'
            # if 'court' in line.lower() or 'panel' in line.lower()) and ('No.' not in line or 'Division No.' in line):
            if any(line_alphanum_chars.startswith(s) for s in docket_numbers_clean):
                state = states["docketnumber"]
            elif line_alphanum_chars.startswith(court_clean) or (
                    (line_text.endswith('Court of Appeals.') or any(line_text_lower.startswith(s) for s in ('court of appeal', 'supreme court')))
            ):
                state = states["court"]
            else:
                state = states["docketnumber"]
            add_el(el, state)
            continue

        # accidental start of opinion included in head matter
        # NW2d/737/737NW2d768_3New.xml -- "On order of the Court ..."
        if state >= states["decisiondate"]:
            if line_text.startswith("On order of the Court"):
                state = states["opinion"]
                add_el(el, 0, opinions[-1])
                continue

        # dates
        # 'DATED at Olympia, Washington, this 31st day of October, 2018.'
        # '01-04-2017'
        if state <= states["decisiondate"]:
            # long line isn't decision date -- SCt/134/134sct985_2.xml
            if len(line_text) < 80 and (date_re.search(line_text) or line_text_lower.startswith('dated at') or re.match(r'\d{1,2}-\d{2}-\d{4}$', line_text)):
                if any(line_text.startswith(s) for s in ('Released', 'Submitted', 'Dissenting')) and 'Decided' not in line_text:
                    # handle case like
                    # 'Submitted June 5, 2007, at Lansing.'
                    # 'Decided June 12, 2007, at 9:05 a.m.'
                    # 'Released for Publication October 11, 2007
                    # 'Dissenting Opinion of Chief Justice Maynard June 27, 2008.'
                    # avoid
                    # 'Submitted March 2, 2010.<br>Decided April 2, 2010.'
                    state = states["otherdate"]
                else:
                    state = states["decisiondate"]
                add_el(el, state)
                continue

        if state < states["judges"]:
            # strip off judges lines appended to current line, and add as an extra_el
            # "for Respondent.<strong>Justice BEATTY.</strong></p>" SE2d/708/708se2d750.xml
            # "... West Virginia Insurance Federation.<strong>DAVIS, Justice:</strong></p>" SE2d/719/719se2d830.xml
            # "for appellees.<strong>Present: HUMPHREYS, McCLANAHAN and BEALES, JJ.</strong><strong>BEALES, Judge.</strong>" SE2d/708/708se2d429.xml
            while True:
                m = re.search('(.+)(<strong>([^<]+)</strong>)$', line)
                if m and is_judges_or_author(m[3]):
                    extra_els.insert(0, PyQuery('<p>'+m[2]+'</p>'))
                    line = m[1]
                    el_pq.html(line)
                    line_text = strip_tags(line)
                    line_alphanum_chars = alphanum_lower(line_text)
                    continue
                break

            # history
            # 'Appeal by defendant from judgment entered 8 December 2004 by Judge Robert H. Hobgood in Alamance County Superior Court. Heard in the Court of Appeals 2 November 2005.'
            if line_text_lower.startswith('appeal') or any(s in line_text for s in ('Superior Court', 'District Court', 'Circuit Court')):
                state = states["history"]
                add_el(el, state)
                continue

            # syllabus
            if 'Syllabus by the Court' in line_text or (state == states["syllabus"] and re.match(r'\d+\.|[a-z\[]', line_text)):
                if re.match(r'[a-z\[]', line_text):
                    # handle case where syllabus is split midsentence
                    append_to_previous(line)
                else:
                    state = states["syllabus"]
                    add_el(el, state)
                continue

            # attorneys
            # 'Garrett D. Blanchfield, Jr., Reinhardt Wendorf & Blanchfield, St. Paul, MN, for Appellants.'
            if any(line_text.startswith(s) for s in ("An amicus", "For the", "On behalf of")) or any(s in line_text for s in (' for ', 'amici curiae', 'pro se')):
                state = states["attorneys"]
                add_el(el, state)
                continue

        # titles that mark the start of an opinion, like "OPINION"
        if line_alphanum_chars in opinion_start_lines or any(line_alphanum_chars.startswith(s) for s in opinion_start_line_prefixes):
            state = states["_opinionstart"]
            if line_text != "OPINION":
                add_el(el, state)
            continue

        # Handle paragraph that is definitely followed by author, like "The opinion of the court was delivered by", A3d/148/148 A.3d 441_Replace.xml
        if line_text == "The opinion of the court was delivered by":
            state = states["_preauthor"]
            add_el(el, 0)
            continue
        if state == states["_preauthor"]:
            add_el(el, states["author"])
            state = states["opinion"]
            continue

        # author
        # note, in theory fastcase_data["Author"] could be useful for identifying author paragraph, but it's often not set,
        # and when it is it can also appear in the judges line and other places ...
        judges_or_author = is_judges_or_author(line_text)
        if judges_or_author == "judges":
            state = states["judges"]
            add_el(el, state)
            continue
        elif judges_or_author == "author":
            add_el(el, states["author"])
            state = states["opinion"] if header_complete else states["author"]
            continue

        # weird special case where there's an order provided before the start of the opinion
        # E.g. NW2d/740/740NW2d659_1.xml, 'ORDER ENTERED JUNE 8, 2007' and subsequent unlabeled lines
        if line_text.startswith("ORDER ENTERED") or state == states["disposition"]:
            state = states["disposition"]
            add_el(el, state)
            continue

        # regular paragraph
        add_el(el, 0)
        continue

    # fixups
    labels = [el.attrib.get('class') for el in header_els]
    # rewrite special case like NE2d/944/944ne2d1119.xml:
    # [['parties', '...'],
    #  ['docketnumber', 'Feb. 15'],
    #  ['docketnumber', '2011.'],
    #  ['court', 'Court of Appeals of New York.']]
    # to
    # [['parties', '...'],
    #  ['court', 'Court of Appeals of New York.'],
    #  ['decisiondate', 'Feb. 15, 2011.']]
    if labels == [None, 'docketnumber', 'docketnumber', 'court']:
        docket_combined = header_els[1].text + ", " + header_els[2].text
        if date_re.match(docket_combined):
            header_els[1].attrib['class'] = 'decisiondate'
            header_els[1].text = docket_combined
            header_els = [header_els[0], header_els[3], header_els[1]]

    # change all author labels but the last to judges; we likely misdetected one earlier
    for i, el in authors[:-1]:
        el.attrib['class'] = "judges"

    # if we didn't find an author and the last line is unlabeled, assume that's the author with a typo --
    # e.g. NW2d/753/753NW2d552_1.xml , missing comma
    if not authors and not opinion_starts and state >= states["judges"] and header_els[-1].attrib.get('class') is None:
        header_els[-1].attrib['class'] = "author"
        authors = [(len(header_els)-1, header_els[-1])]

    # move author, and any paragraphs after it, to beginning of first opinion
    move_index = opinion_starts[0][0] + 1 if opinion_starts else authors[-1][0] if authors else None
    if move_index is not None:
        shift_to_opinion(len(header_els)-move_index)

    return header_els, opinions


def make_case_el(case, header_els, opinions):
    """Return a new CAP html case as an lxml tree."""
    case_el = renderer.make_case_el(case)
    case_el.text = "\n"

    # head matter
    head_el = renderer.make_opinion_el({'type': 'head'})
    if header_els:
        head_el.text = "\n"
        head_el.extend(header_els)
    case_el.append(head_el)
    # opinions
    for opinion_els in opinions:

        # add body to case
        if opinion_els:
            opinion_type = opinion_els[0].attrib.pop('opinion-type', 'majority')
        else:
            opinion_type = 'majority'
        body_el = renderer.make_opinion_el({'type': opinion_type})
        if opinion_els:
            body_el.text = "\n"
            body_el.extend(opinion_els)
        case_el.append(body_el)
    return case_el


def fix_footnotes(case_el, warnings):
    """
        Find footnotes and footnote references and update to CAP format.
        Append any additional warnings to warnings list.
    """
    case_pq = PyQuery(case_el)
    # fix footnotes
    # footnotes look like this (since <small> is already stripped)
    #       <p>--------</p>
    #       <p>Notes:</p>
    #       <p>
    #           <sup>
    #             <a href="#fn1" name="fr1">1</a>
    #           </sup> text text text </p>
    # notes label can look like `<strong><br/> --------</strong>` -- NE2d/990/990ne2d139_12.xml
    notes_el = case_pq('p:contains("Notes:")').filter(lambda i, el: strip_tags(PyQuery(el).text()).strip() == 'Notes:')
    refs = {}
    notes_section = None
    if notes_el:
        notes_section = notes_el.closest('article, section')
        footnote_index = 0
        opinion_index = 1
        footnote_el = None

        # before and after footnote sections there is a paragraph of either 8 or 15 hyphens
        footnote_breaks = ['-' * 8, '-' * 15]

        # remove footnote break before footnote section
        # can have tags in the footnote break -- A3d/50/50a3d607_29.xml
        prev_notes_el = notes_el.prev()
        if strip_tags(prev_notes_el.text()).strip() not in footnote_breaks:
            warnings.append("Unexpected element before notes el.")
        else:
            prev_notes_el.remove()

        # remove "Notes:"
        old_footnote_el = notes_el.next()
        notes_el.remove()

        # step through each footnote element
        while old_footnote_el:
            # sometimes <a> tag gets out of <p> tag -- SE2d/590/590SE2d53.xml
            # put it inside a new <p>
            if old_footnote_el[0].tag == 'a':
                old_footnote_el = wrap_with(old_footnote_el, PyQuery(etree.Element('p')))

            link_el = old_footnote_el('a').eq(0)
            if not link_el:
                # this could be the end of footnotes, in which case stop
                if strip_tags(old_footnote_el.text()).strip() in footnote_breaks:
                    old_footnote_el.remove()
                    break
                # or could be a second paragraph of the previous footnote, in which case append
                if footnote_el:
                    footnote_el.append(old_footnote_el)
                    old_footnote_el = footnote_el.next()
                    continue
                else:
                    # if there's a non-footnote before the first footnote, we don't know what's going on,
                    # so quit processing
                    warnings.append("Unexpected non-footnote element.")
                    break
            label = link_el.text()
            footnote_index += 1
            footnote_id = f'footnote_{opinion_index}_{footnote_index}'
            footnote_el = PyQuery(renderer.make_footnote_el(id=footnote_id, label=label))
            refs[link_el.attr('href').lstrip('#')] = [footnote_id, footnote_el]
            while link_el.parent()[0].tag == 'sup':
                link_el = link_el.parent()
            link_el.remove()

            # remove space at beginning of footnote left over from removing footnote number
            if old_footnote_el[0].text:
                old_footnote_el[0].text = old_footnote_el[0].text.lstrip()

            wrap_with(old_footnote_el, footnote_el)
            old_footnote_el = footnote_el.next()

    # fix footnote references (<small> is already stripped)
    # ...<sup><a href="#fr1" name="fn1">1</a></sup>...  typical
    # ...<sup id="co_fnRef_B00012045229866_ID0E4F">1</sup>  BR/590/590 B.R. 577.xml
    # ...<a href="#1" name="fn1" id="fn1">1</a>...  NW2d/781/781NW2d5512010WIApp33_29.xml
    for section in case_pq('.head-matter, .opinion').items():
        for old_ref_pq in section('a, sup[id]').items():
            label = old_ref_pq.text()
            if old_ref_pq[0].tag == 'a':
                ref_name = old_ref_pq.attr('name')
                if not (ref_name and ref_name.startswith('fn')):
                    continue
            else:
                ref_name = "fn" + label
            ref, footnote_el = refs.get(ref_name, ['orphan', None])
            if footnote_el:
                # move footnotes from end of document to correct section -- see NW2d/906/906 N.W.2d 436_Replace.xml
                if section != notes_section:
                    section.append(footnote_el)
            else:
                warnings.append(f"Unmatched ref {repr(str(old_ref_pq))}")
            ref_el = etree.Element('a', {'class': 'footnotemark', 'href': '#' + ref, 'id': 'ref_' + ref})
            ref_el.text = label
            while old_ref_pq.parent()[0].tag == 'sup':
                old_ref_pq = old_ref_pq.parent()
            PyQuery(ref_el).insert_before(old_ref_pq)
            old_ref_pq.remove()


def html_to_xml(case_el):
    """
        Rewrite our case HTML format to XML.
        (This could potentially be used for CAP cases as well as Fastcase, avoiding the need to re-render our
         cases both ways, but might need additional testing/cases handled).
    """
    case_el = PyQuery(deepcopy(case_el))

    # fix case_el
    el = case_el[0]
    el.tag = 'casebody'
    for attr in ('firstpage', 'lastpage'):
        el.attrib[attr] = el.attrib.pop(f'data-{attr}')
    el.attrib.pop('class')
    el.attrib.pop('data-case-id')
    el.attrib['xmlns'] = 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1'

    # remove sections where contents go outside wrapper
    head_el = case_el('section.head-matter, section.unprocessed, section.corrections')
    head_el.after(head_el.children())
    head_el.remove()

    # update opinions
    for el in case_el('article.opinion'):
        el.tag = 'opinion'
        el.attrib.pop('class')
        el.attrib['type'] = el.attrib.pop('data-type')

    # update paragraphs
    for el in case_el('p[class]'):
        el.tag = el.attrib.pop('class')

    # update footnotes
    for el in case_el('aside.footnote'):
        el.tag = 'footnote'
        for attr in ('label', 'orphan'):
            val = el.attrib.pop(f'data-{attr}', None)
            if val:
                el.attrib[attr] = val
        el.attrib.pop('class')
        el.attrib.pop('id')
        if len(el) and el[0].tag == 'a':
            el.remove(el[0])

    # update footnote refs
    for el in case_el('a.footnotemark'):
        el.tag = 'footnotemark'
        el.attrib.pop('class')
        el.attrib.pop('href')
        el.attrib.pop('id')

    return case_el[0]


## entry points ##

def format_fastcase_html(case):
    return format_fastcase_html_from_parts(case, case.citations.all(), case.fastcase_import.data)


def format_fastcase_html_from_parts(case, citations, fastcase_data):
    # collect initial HTML from fastcase_data and reformat it for parsing by lxml
    html = prepare_html_for_tidy(fastcase_data)
    html, warnings = html_tidy(html)
    html = post_tidy_html_fixes(html)

    # parse html to lxml tree
    parsed_html = etree.HTML('<root>' + html + '</root>')

    # Process each paragraph of html, in two stages. The first stage detects and reformats page numbers, merges
    # paragraphs that are split by page numbers, removes empty or redacted paragraphs, and otherwise resegments the
    # paragraphs. The second phase heuristically attempts to label each paragraph, returning the labeled header
    # paragraphs and the paragraphs for each opinion in the case.
    segment_paragraphs(parsed_html, citations)
    header_els, opinions = label_paragraphs(parsed_html, fastcase_data)

    # Combine the individual paragraphs into a case in CAP html
    case_el = make_case_el(case, header_els, opinions)

    # Fix footnotes and footnote references
    fix_footnotes(case_el, warnings)

    # Clean up HTML for output
    remove_empty_tags(case_el, ignore_tags={'br', 'article', 'section'})
    reindent(case_el)

    # Convert HTML to XML and clean up for output
    xml_case_el = html_to_xml(case_el)
    reindent(xml_case_el)

    return {
        'html': etree.tostring(case_el, encoding=str, method='html'),
        'xml': etree.tostring(xml_case_el, encoding=str, method='xml'),
    }

