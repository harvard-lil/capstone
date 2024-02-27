import re
import unicodedata
from collections import defaultdict
from functools import lru_cache, partial
from itertools import groupby
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
from scripts.helpers import serialize_xml, parse_xml, serialize_html, alphanum_lower, parse_html, clean_punctuation


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

    def no_cites_found():
        return html, xml, [c.id for c in case.extracted_citations.all()], []

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

    for i, section in enumerate(clean_html_pq('.head-matter, .opinion').items()):
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
                normalized_forms['normalized_cite'] = alphanum_lower(normalized_forms['cite'])
                normalized_forms['rdb_cite'] = eyecite_cite.corrected_citation()
                normalized_forms['rdb_normalized_cite'] = alphanum_lower(normalized_forms['rdb_cite'])
                eyecite_cite.normalized_forms = normalized_forms

                for k, v in normalized_forms.items():
                    cites_by_type[k].append(v)

            if extracted_cites:
                extracted_els.append((el.attr("id"), el_text, extracted_cites))

    # short circuit if no cites found
    if not extracted_els:
        return no_cites_found()

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
            Q(rdb_normalized_cite__in=cites_by_type['rdb_normalized_cite']))
        .select_related('case')
    )
    for cite in target_cites:
        for cite_type in cites_by_type:
            cite_str = getattr(cite, cite_type)
            if cite_str:
                cases_by_cite[cite_type][cite_str].add(cite.case)

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
            corrected_cite = first_cite.corrected_citation()
            case_ids_attr = None

            # get URL attributes for link annotation
            if isinstance(resolution, Resource):
                target_url = cite_home_url + "/citations/?q=" + urllib.parse.quote(corrected_cite)
            else:
                # cite resolved to a tuple of CaseMetadata objects
                case_ids_attr = ','.join(sorted(str(r.id) for r in resolution))
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
            target_url = target_url.replace(settings.PARENT_HOST, settings.CACHED_PARENT_HOST)

            # get tag text for link annotation
            span = eyecite_cite.span()
            html_annotations.append((
                span,
                f'<a href="{target_url}" class="citation" data-index="{cite_index}" data-cite="{corrected_cite}"' +
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
                # for annotation to work reliably, we want to replace long html blocks like page numbers
                # with single unicode characters so the diff between text and html is reliable in the annotate function.
                # then once we get the result we replace back.
                el_html = annot_el.html()
                strings_to_protect = re.findall(r'<a[^>]*>.*?</a>|<[^>]+>', el_html, flags=re.S)
                el_html, char_mapping = encode_strings_as_unicode(el_html, strings_to_protect)
                el_html = annotate(el_text, annotations, el_html, annotator=partial(annotator, char_mapping))
                el_html = decode_unicode_to_strings(el_html, char_mapping)
                annot_el.html(el_html)

    # make each ExtractedCitation
    for resolution, cluster in clusters.items():
        opinion_clusters = {k:list(v) for k,v in groupby(sorted(cluster, key=lambda c: c.opinion_id), lambda c: c.opinion_id)}

        # pull selected metadata from first cite
        first_cite: FullCitation = cluster[0]
        normalized_forms = first_cite.normalized_forms
        reporter = first_cite.corrected_reporter()
        first_reporter = first_cite.all_editions[0].reporter
        category = f"{first_reporter.source}:{first_reporter.cite_type}"
        groups = first_cite.groups or {}
        year = first_cite.year

        metadata = {k: v for k, v in first_cite.metadata.__dict__.items() if v}
        if isinstance(resolution, tuple):
            target_cases = [m.id for m in resolution]
            target_case_id = target_cases[0] if len(target_cases) == 1 else None
        else:
            target_cases = []
            target_case_id = None

        for opinion_id, opinion_cluster in opinion_clusters.items():
            # collect pin cites
            pin_cites = []
            for cite in opinion_cluster:
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
            weight = len(opinion_cluster)

            # NOTE if adding any fields here, also add to cite_key()
            extracted_cite = ExtractedCitation(
                **normalized_forms,
                reporter=reporter,
                category=category,
                cited_by=case,
                target_case_id=target_case_id,
                target_cases=target_cases,
                groups=groups,
                metadata=metadata,
                pin_cites=pin_cites,
                weight=weight,
                year=year,
                opinion_id=opinion_id,
            )

            found_cites.append(extracted_cite)

    if not found_cites:
        return no_cites_found()

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
            cites_to_delete.append(e.id)
    cites_to_create = new_cites_lookup.values()

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
        cites.append((matched_text, alphanum_lower(matched_text), alphanum_lower(canonical_cite)))
    return list(dict.fromkeys(cites).keys())  # remove dupes while retaining order


def extract_whole_cite(text, require_classes=(CaseCitation,), ignore_classes=(NonopinionCitation,)):
    """Return eyecite cite only if entire text is matched as a single cite. Otherwise return None."""
    cites = list(extract_citations_from_text(text, require_classes, ignore_classes))
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


def clean_text(text):
    """
        Prepare text for cite extraction by normalizing punctuation and unicode characters.
        >>> assert clean_text("“”–—´ ‘ ’ñâüÍí") == '''""--' ' 'nauIi'''
    """
    # normalize punctuation
    text = clean_punctuation(text)
    # strip unicode Nonspacing Marks (umlauts, accents, etc., usually OCR speckles)
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text


def encode_strings_as_unicode(big_string, substrings):
    """ Replace substrings in big_string with unique characters in the unicode private use range. """
    char_mapping = []
    for i, substring in enumerate(substrings):
        unicode_char = chr(0xE000 + i)  # start of the private use range
        char_mapping.append([substring, unicode_char])
        big_string = big_string.replace(substring, unicode_char, 1)
    return big_string, char_mapping


def decode_unicode_to_strings(big_string, char_mapping):
    """Undo encode_strings_as_unicode by replacing each pair in char_mapping."""
    for s, c in char_mapping:
        big_string = big_string.replace(c, s)
    return big_string


def annotator(char_mapping, before, encoded_text, after):
    """
        Attach annotation tags to a stretch of citation text. If text contains a link or an unbalanced tag, wrap
        those tags.
    """
    text = decode_unicode_to_strings(encoded_text, char_mapping)
    if '<a' in text or not is_balanced_html(text):
        encoded_text = re.sub(r'[\uE000-\uF8FF]', rf"{after}\g<0>{before}", encoded_text)
    return before + encoded_text + after


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
