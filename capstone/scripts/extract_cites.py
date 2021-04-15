import re
import unicodedata
from collections import defaultdict
from functools import lru_cache, partial

from django.conf import settings
from django.db.models import Q
from django.utils.text import slugify
from eyecite import annotate
from eyecite.find_citations import get_citations
from eyecite.models import FullCaseCitation, CaseCitation
from eyecite.tokenizers import HyperscanTokenizer, EXTRACTORS
from eyecite.utils import is_balanced_html

from capweb.helpers import reverse
from scripts.helpers import serialize_xml, parse_xml, serialize_html, normalize_cite, parse_html


### ENTRY POINTS ###

def extract_citations(case, html, xml):
    """
        Given a case along with its html and xml, return the html and xml annotated with citation tags,
        as well as a list of any existing ExtractedCitation objects to delete and any new ExtractedCitation
        objects to create.
    """
    from capdb.models import ExtractedCitation, Citation  # avoid circular imports

    found_cites = False
    cite_index = 0
    cites_to_delete = {cite_key(e): e for e in case.extracted_citations.all()}
    cites_to_create = []
    self_cites = {c.normalized_cite for c in case.citations.all()}
    extracted_els = []
    cites_by_type = {'cite': [], 'normalized_cite': [], 'rdb_cite': [], 'rdb_normalized_cite': []}

    # Annotation is faster if we extract paragraph by paragraph. So first get an index of each paragraph in the
    # html and xml to insert annotations into, and parse a cleaned version of the source html to extract citations
    # from:
    html_pq = parse_html(html)
    html_els = {el.attr('id'): el for el in html_pq('[id]').items()}
    xml_pq = parse_xml(xml)
    xml_els = {el.attr('id'): el for el in xml_pq('[id]').items()}
    clean_html_pq = parse_html(clean_text(html))
    clean_html_pq('.page-label').remove()


    # Extract cites from each paragraph:
    for el in clean_html_pq('p[id], blockquote[id]').items():
        el_text = el.text()
        extracted_cites = []
        for eyecite_cite in extract_citations_from_text(el_text):

            # get normalized forms of cite
            cite = {'cite': eyecite_cite.matched_text()}
            cite['normalized_cite'] = normalize_cite(cite['cite'])
            reporter_corrected, cite['rdb_cite'] = canonicalize_cite(eyecite_cite)
            cite['rdb_normalized_cite'] = normalize_cite(cite['rdb_cite'])

            # skip citations to self, typically from parallel cites in header
            if cite['normalized_cite'] in self_cites or cite['rdb_normalized_cite'] in self_cites:
                continue

            extracted_cites.append((eyecite_cite, cite, reporter_corrected))
            for k, v in cite.items():
                cites_by_type[k].append(v)

        if extracted_cites:
            extracted_els.append((el.attr("id"), el_text, extracted_cites))

    # Look up cases referred to by cites. cases_by_cite gets populated like:
    #   cases_by_cite['cite']['1 U.S. 1'] = {(<case_id>, <decision_date_original>, <frontend_url>)}
    cases_by_cite = {c: defaultdict(set) for c in cites_by_type}
    target_cites = (Citation
        .objects
        .filter(case__in_scope=True)
        .filter(
            Q(cite__in=cites_by_type['cite']) |
            Q(cite__in=cites_by_type['normalized_cite']) |
            Q(cite__in=cites_by_type['rdb_cite']) |
            Q(cite__in=cites_by_type['rdb_normalized_cite'])
        )
        .values('case_id', 'case__decision_date_original', 'case__frontend_url', 'cite', 'normalized_cite', 'rdb_cite', 'rdb_normalized_cite'))
    for cite in target_cites:
        for cite_type in cites_by_type:
            if cite[cite_type]:
                cases_by_cite[cite_type][cite[cite_type]].add((cite['case_id'], cite['case__decision_date_original'], cite['case__frontend_url']))

    # Create each ExtractedCitation and annotate each paragraph:
    for el_id, el_text, extracted_cites in extracted_els:
        html_annotations = []
        xml_annotations = []
        for eyecite_cite, cite, reporter_corrected in extracted_cites:

            # get potential case or cases pointed to by cite
            matches = list(
                cases_by_cite['cite'].get(cite['cite']) or
                cases_by_cite['normalized_cite'].get(cite['normalized_cite']) or
                cases_by_cite['rdb_cite'].get(cite['rdb_cite']) or
                cases_by_cite['rdb_normalized_cite'].get(cite['rdb_normalized_cite'], set())
            )

            # filter matches by date
            if len(matches) > 1:
                matches = [i for i in matches if i[1] <= case.decision_date_original]

            # get URL attributes for link annotation
            if len(matches) == 1:
                target_case_id = matches[0][0]
                target_url = matches[0][2]
            else:
                target_case_id = None
                target_url = reverse(
                    'citation',
                    host='cite',
                    args=[slugify(reporter_corrected), slugify(eyecite_cite.volume or '1'), eyecite_cite.page])
            case_ids_attr = ','.join(str(m[0]) for m in matches)

            # get tag text for link annotation
            span = eyecite_cite.span()
            html_annotations.append((
                span,
                f'<a href="{target_url}" class="citation" data-index="{cite_index}"' +
                (f' data-case-ids="{case_ids_attr}"' if case_ids_attr else '') + '>',
                '</a>'
            ))
            xml_annotations.append((
                span,
                f'<extracted-citation url="{target_url}" index="{cite_index}"' +
                (f' case-ids="{case_ids_attr}"' if case_ids_attr else '') + '>',
                '</extracted-citation>'
            ))
            cite_index += 1

            # create new cite
            # NOTE if adding any fields here, also add to cite_key()
            extracted_cite = ExtractedCitation(
                cite=cite['cite'],
                normalized_cite=cite['normalized_cite'],
                rdb_cite=cite['rdb_cite'],
                rdb_normalized_cite=cite['rdb_normalized_cite'],
                cited_by=case,
                target_case_id=target_case_id,
                target_cases=[m[0] for m in matches],
                reporter_name_original=eyecite_cite.reporter_found,
                volume_number_original=eyecite_cite.volume,
                page_number_original=eyecite_cite.page)

            # if we already have this one, skip saving; else add
            extracted_cite_key = cite_key(extracted_cite)
            if extracted_cite_key in cites_to_delete:
                cites_to_delete.pop(extracted_cite_key)
            else:
                cites_to_create.append(extracted_cite)

            found_cites = True

        # annotate paragraph in html and xml
        if html_annotations:
            for annot_el, annotations in ((xml_els[el_id], xml_annotations), (html_els[el_id], html_annotations)):
                annot_el.html(annotate(el_text, annotations, annot_el.html(), annotator=annotator))

    # serialize annotated html and xml
    if found_cites:
        html = serialize_html(html_pq)
        xml = serialize_xml(xml_pq).decode('utf8')

    cites_to_delete = list(cites_to_delete.values())
    return html, xml, cites_to_delete, cites_to_create


def extract_citations_normalized(text):
    """
        Given source text, return each unique tuple of (matched text, normalized cite, normalized canonical cite).
        For example:
        >>> assert extract_citations_normalized("foo 1 Mass.App. 1 bar") == [("1 Mass.App. 1", "1massapp1", "1massappct1")]
    """
    cites = []
    for eyecite_cite in extract_citations_from_text(text):
        matched_text = eyecite_cite.matched_text()
        canonical_cite = canonicalize_cite(eyecite_cite)[1]
        cites.append((matched_text, normalize_cite(matched_text), normalize_cite(canonical_cite)))
    return list(dict.fromkeys(cites).keys())  # remove dupes while retaining order


def extract_whole_cite(text):
    """Return eyecite cite only if entire text is matched as a single cite. Otherwise return None."""
    cites = list(extract_citations_from_text(text))
    if len(cites) == 1 and cites[0].matched_text() == text:
        return cites[0]
    return None


### INTERNAL CITE EXTRACTION HELPERS ###

def extract_citations_from_text(text):
    """Do the actual work of fetching each eyecite cite object."""
    cite_extractor = get_cite_extractor()
    for cite in cite_extractor(text):
        if not isinstance(cite, CaseCitation):
            continue
        yield cite


@lru_cache(None)
def get_cite_extractor():
    """
        Return a version of eyecite's get_citations() that uses HyperscanTokenizer and uses more flexible regexes
        to match our OCR.
    """

    # Within reporter names OCR may show zero or a few of [period, hyphen, comma, quote]
    # where there's supposed to be a space or period.
    MID_CRUFT = r"[ ,.\-']{0,3}"
    # We accept one or two characters of OCR noise after a reporter name.
    # Can't accept more than two without getting into matching things we shouldn't like "123 U. S.-, 456 S.Ct. 789"
    END_CRUFT = r"[,.\-']{0,2}"

    def add_cruft(m):
        return m[1] + MID_CRUFT.join(i for i in re.split(r'(?:\\?\.|\s|\\? )+', m[2]) if i) + END_CRUFT + m[3]

    for extractor in EXTRACTORS:
        if '(?P<reporter>' not in extractor.regex:
            continue
        extractor.regex = re.sub(r'(\(\?P<reporter>)(.*?)(\)),\?', add_cruft, extractor.regex)

    tokenizer = HyperscanTokenizer(cache_dir=settings.HYPERSCAN_CACHE_DIR)
    return partial(get_citations, tokenizer=tokenizer)


def canonicalize_cite(cite):
    """
        Get the canonical form of a citation's reporter and text given an eyecite cite object. For example:
        >>> assert canonicalize_cite(list(extract_citations_from_text("1 Mass,App 1"))[0]) == ('Mass. App. Ct.', '1 Mass. App. Ct. 1')
        >>> assert canonicalize_cite(list(extract_citations_from_text("1 Mass,App, at 1"))[0]) == ('Mass. App. Ct.', '1 Mass. App. Ct. 1')
    """
    if cite.edition_guess:
        reporter_corrected = cite.edition_guess.short_name
    else:
        reporter_guesses = set(e.short_name for e in cite.all_editions)
        if len(reporter_guesses) != 1:
            # no single correct reporter identified, so return original cite found
            return cite.reporter_found, cite.matched_text()
        reporter_corrected = reporter_guesses.pop()
    if isinstance(cite, FullCaseCitation):
        # full cites might have non-standard formatting, so replace reporter to correct them
        cite_corrected = cite.matched_text().replace(cite.reporter_found, reporter_corrected)
    else:
        # short cites are currently only found with standard formatting
        cite_corrected = f"{cite.volume} {reporter_corrected} {cite.page}"
    return reporter_corrected, cite_corrected


_clean_text_table = str.maketrans("“”–—´‘’", "\"\"--'''")


def clean_text(text):
    """
        Prepare text for cite extraction by normalizing punctuation and unicode characters.
        >>> assert clean_text("“”–—´ ‘ ’ñâüÍí") == '''""--' ' 'nauIi'''
    """
    # normalize punctuation
    text = text.translate(_clean_text_table)
    # strip unicode Nonspacing Marks (umlauts, accents, etc., usually OCR speckles)
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text


def annotator(before, text, after):
    """
        Attach annotation tags to a stretch of citation text. If text contains a link or an unbalanced tag, wrap
        those tags:
        >>> assert annotator("<tag>", "foo", "</tag>") == "<tag>foo</tag>"
        >>> assert annotator("<tag>", "foo<em>bar", "</tag>") == "<tag>foo</tag><em><tag>bar</tag>"
        >>> assert annotator("<tag>", "foo<a>bar</a>baz", "</tag>") == "<tag>foo</tag><a>bar</a><tag>baz</tag>"
    """
    if '<a' in text or not is_balanced_html(text):
        text = re.sub(r"<a[^>]*>.*?</a>|<[^>]+>", rf"{after}\g<0>{before}", text)
    return before + text + after


def cite_key(extracted_cite):
    """Get a hashable key to represent a given ExtractedCite object, to check whether a new one is redundant."""
    return (
        extracted_cite.cite,
        extracted_cite.normalized_cite,
        extracted_cite.rdb_cite,
        extracted_cite.rdb_normalized_cite,
        extracted_cite.cited_by_id,
        extracted_cite.target_case_id,
        tuple(extracted_cite.target_cases) if extracted_cite.target_cases else None,
        extracted_cite.reporter_name_original,
        extracted_cite.volume_number_original,
        extracted_cite.page_number_original,
    )
