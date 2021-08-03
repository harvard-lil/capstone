import re
import unicodedata
from collections import defaultdict
from functools import lru_cache, partial
import urllib.parse

from django.conf import settings
from django.db.models import Q
from django.utils.text import slugify
from eyecite import annotate, resolve_citations
from eyecite.find_citations import get_citations
from eyecite.models import FullCaseCitation, CaseCitation, NonopinionCitation, FullCitation, Resource
from eyecite.resolve import resolve_full_citation
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

    found_cites = []
    cite_index = 0
    extracted_els = []
    cites_by_type = {'cite': [], 'normalized_cite': [], 'rdb_cite': [], 'rdb_normalized_cite': []}
    eyecite_cites = []
    cite_home_url = reverse('cite_home').rstrip('/')

    # Annotation is faster if we extract paragraph by paragraph. So first get an index of each paragraph in the
    # html and xml to insert annotations into, and parse a cleaned version of the source html to extract citations
    # from:
    html_pq = parse_html(html)
    html_els = {el.attr('id'): el for el in html_pq('[id]').items()}
    xml_pq = parse_xml(xml)
    xml_els = {el.attr('id'): el for el in xml_pq('[id]').items()}
    clean_html_pq = parse_html(clean_text(html))
    clean_html_pq('a').remove()

    # Extract cites from each paragraph for each opinion:
    for i, section in enumerate(clean_html_pq('.opinion').items()):
        for el in section('p[id], blockquote[id]').items():
            el_text = el.text()
            extracted_cites = []
            for eyecite_cite in extract_citations_from_text(el_text, require_classes=None):
                eyecite_cites.append(eyecite_cite)
                extracted_cites.append(eyecite_cite)
                eyecite_cite.opinion_id = i

                if not isinstance(eyecite_cite, FullCitation):
                    continue

                # get normalized forms of cite
                normalized_forms = {'cite': eyecite_cite.matched_text()}
                normalized_forms['normalized_cite'] = normalize_cite(normalized_forms['cite'])
                normalized_forms['rdb_cite'] = eyecite_cite.corrected_citation()
                normalized_forms['rdb_normalized_cite'] = normalize_cite(normalized_forms['rdb_cite'])
                eyecite_cite.normalized_forms = normalized_forms

                for k, v in normalized_forms.items():
                    cites_by_type[k].append(v)

            if extracted_cites:
                extracted_els.append((el.attr("id"), el_text, extracted_cites))

    # short circuit if no cites found
    if not extracted_els:
        # delete all existing cites
        return html, xml, list(case.extracted_citations.all()), []

    # Look up cases referred to by cites. cases_by_cite gets populated like:
    #   cases_by_cite['cite']['1 U.S. 1'] = {(<case_id>, <decision_date_original>, <frontend_url>)}
    cases_by_cite = {c: defaultdict(set) for c in cites_by_type}
    target_cites = (Citation
        .objects
        .filter(case__in_scope=True)
        .filter(
            Q(cite__in=cites_by_type['cite']) |
            Q(normalized_cite__in=cites_by_type['normalized_cite']) |
            Q(rdb_cite__in=cites_by_type['rdb_cite']) |
            Q(rdb_normalized_cite__in=cites_by_type['rdb_normalized_cite'])
        ))
    for cite in target_cites:
        for cite_type in cites_by_type:
            cite_str = getattr(cite, cite_type)
            if cite_str:
                cases_by_cite[cite_type][cite_str].add(cite.case)

    # cluster cites by the resources they refer to
    def resolve_full_cite(eyecite_cite):
        # use builtin resolver for non-case citations
        if not isinstance(eyecite_cite, FullCaseCitation):
            return resolve_full_citation(eyecite_cite)

        normalized_forms = eyecite_cite.normalized_forms

        # get potential case or cases pointed to by cite
        matches = tuple(
            cases_by_cite['cite'].get(normalized_forms['cite']) or
            cases_by_cite['normalized_cite'].get(normalized_forms['normalized_cite']) or
            cases_by_cite['rdb_cite'].get(normalized_forms['rdb_cite']) or
            cases_by_cite['rdb_normalized_cite'].get(normalized_forms['rdb_normalized_cite'], set())
        )

        # filter matches by date
        if len(matches) > 1:
            year_matches = tuple(i for i in matches if i.decision_date_original <= case.decision_date_original)
            if year_matches:
                matches = year_matches

        if matches:
            return matches
        return resolve_full_citation(eyecite_cite)

    clusters = resolve_citations(eyecite_cites, resolve_full_citation=resolve_full_cite)
    # skip citations to self, typically from parallel cites in header
    clusters = {k: v for k, v in clusters.items() if not isinstance(k, tuple) or case not in k}
    resolution_by_cite = {cite: resolution for resolution, cites in clusters.items() for cite in cites}

    # annotate each citation:
    for el_id, el_text, extracted_cites in extracted_els:
        html_annotations = []
        xml_annotations = []
        for eyecite_cite in extracted_cites:
            # skip short cites that didn't match to anything
            if eyecite_cite not in resolution_by_cite:
                continue

            resolution = resolution_by_cite[eyecite_cite]
            first_cite = clusters[resolution][0]
            case_ids_attr = None

            # get URL attributes for link annotation
            if isinstance(resolution, Resource):
                target_url = cite_home_url + "/citations/?q=" + urllib.parse.quote(first_cite.corrected_citation())
            else:
                # cite resolved to a tuple of CaseMetadata objects
                case_ids_attr = ','.join(str(r.id) for r in resolution)
                if len(resolution) == 1:
                    # attempt to jump directly to cited page, if pin cite starts with digits
                    pin_cite = ''
                    if first_cite.metadata.pin_cite:
                        m = re.match(r'\d+', first_cite.metadata.pin_cite)
                        if m:
                            pin_cite = f'#p{m[0]}'
                    target_url = cite_home_url + resolution[0].frontend_url + pin_cite
                else:
                    target_url = reverse(
                        'citation',
                        host='cite',
                        args=[
                            slugify(first_cite.corrected_reporter()),
                            slugify(first_cite.groups.get('volume') or '1'),
                            first_cite.groups.get('page')])

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

        # annotate paragraph in html and xml
        if html_annotations:
            for annot_el, annotations in ((xml_els[el_id], xml_annotations), (html_els[el_id], html_annotations)):
                annot_el.html(annotate(el_text, annotations, annot_el.html(), annotator=annotator))

    # make each ExtractedCitation
    for resolution, cluster in clusters.items():
        filtered_cluster = [cite for cite in cluster if isinstance(cite, FullCitation)]

        # pull selected metadata from first cite
        first_cite: FullCitation = filtered_cluster[0]
        normalized_forms = first_cite.normalized_forms
        reporter = first_cite.corrected_reporter()
        weight = len(cluster)
        first_reporter = first_cite.all_editions[0].reporter
        category = f"{first_reporter.source}:{first_reporter.cite_type}"
        
        metadata = {k: v for k, v in first_cite.metadata.__dict__.items() if v}
        if isinstance(resolution, tuple):
            target_cases = [m.id for m in resolution]
            target_case_id = target_cases[0] if len(target_cases) == 1 else None
        else:
            target_cases = []
            target_case_id = None

        # collect pin cites
        pin_cites = []
        for cite in cluster:
            extra = {}
            if getattr(cite.metadata, 'parenthetical'):
                extra['parenthetical'] = cite.metadata.parenthetical
            if getattr(cite.metadata, 'pin_cite'):
                page = cite.metadata.pin_cite or ''
                if page.startswith('at '):
                    page = page[3:]
                extra['page'] = page
            if extra:
                pin_cites.append(extra)

        opinion_includes_cite = {}

        for cite in filtered_cluster:
            # If citation is already included in this opinion, skip
            if cite.opinion_id in opinion_includes_cite:
                continue

            # NOTE if adding any fields here, also add to cite_key()
            extracted_cite = ExtractedCitation(
                **normalized_forms,
                reporter=weight,
                category=category,
                cited_by=case,
                target_case_id=target_case_id,
                target_cases=target_cases,
                groups=cite.groups or {},
                metadata=metadata,
                pin_cites=pin_cites,
                weight=weight,
                year=cite.year,
                opinion_id=cite.opinion_id,
            )

            found_cites.append(extracted_cite)
            opinion_includes_cite[cite.opinion_id] = True 

    if found_cites:
        # serialize annotated html and xml
        html = serialize_html(html_pq)
        xml = serialize_xml(xml_pq).decode('utf8')

        # compare newly found cites to existing ones in db
        new_cites_lookup = {cite_key(c): c for c in found_cites}
        cites_to_delete  = []
        for e in case.extracted_citations.all():
            key = cite_key(e)
            if key in new_cites_lookup:
                new_cites_lookup.pop(key)
            else:
                cites_to_delete.append(e)
        cites_to_create = new_cites_lookup.values()

    else:
        cites_to_delete = list(case.extracted_citations.all())
        cites_to_create = []

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
        canonical_cite = eyecite_cite.corrected_citation()
        cites.append((matched_text, normalize_cite(matched_text), normalize_cite(canonical_cite)))
    return list(dict.fromkeys(cites).keys())  # remove dupes while retaining order


def extract_whole_cite(text):
    """Return eyecite cite only if entire text is matched as a single cite. Otherwise return None."""
    cites = list(extract_citations_from_text(text))
    if len(cites) == 1 and cites[0].matched_text() == text:
        return cites[0]
    return None


### INTERNAL CITE EXTRACTION HELPERS ###

def extract_citations_from_text(text, require_classes=(CaseCitation,), ignore_classes=(NonopinionCitation,)):
    """Do the actual work of fetching each eyecite cite object."""
    cite_extractor = get_cite_extractor()
    for cite in cite_extractor(text):
        if require_classes and not isinstance(cite, require_classes):
            continue
        elif ignore_classes and isinstance(cite, ignore_classes):
            continue
        if cite.matched_text() == "1 FLP 1":
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
    """Get a hashed key to represent a given ExtractedCite object, to check whether a new one is redundant."""
    return hash((
        extracted_cite.cite,
        extracted_cite.normalized_cite,
        extracted_cite.rdb_cite,
        extracted_cite.rdb_normalized_cite,
        extracted_cite.reporter,
        extracted_cite.category,
        extracted_cite.cited_by_id,
        extracted_cite.target_case_id,
        extracted_cite.opinion_id,
        tuple(extracted_cite.target_cases) if extracted_cite.target_cases else None,
        frozenset(extracted_cite.groups.items()) if extracted_cite.groups else None,
        frozenset(extracted_cite.metadata.items()) if extracted_cite.metadata else None,
        tuple(frozenset(p.items()) for p in extracted_cite.pin_cites) if extracted_cite.pin_cites else None,
        extracted_cite.weight,
        extracted_cite.year,
    ))
