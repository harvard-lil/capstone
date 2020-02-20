import re
from reporters_db import REPORTERS, VARIATIONS_ONLY
from capdb.models import ExtractedCitation, Reporter, VolumeMetadata, Citation


def extract(case_text):
    """
    Takes case text and returns two lists:
    a dict of citations that we think exist set to likely reporters
    and a list of strings that look like citations but don't match reporters
    """
    results = re.finditer(r"\d+\s+\w+\.?\s?\w+?\'?\.*\s?\d+\w?\s?\d+", case_text)
    citation_hits = {}
    citation_misses = []
    for result in results:
        citation = result.group()
        parts = citation.split(" ")
        # citation: volume number, reporter short name, page number
        rep_short_name = " ".join(parts[1:-1])
        if rep_short_name in REPORTERS:
            # check if exists as official or variation name
            citation_hits[citation] = rep_short_name
        elif rep_short_name in VARIATIONS_ONLY:
            citation_hits[citation] = VARIATIONS_ONLY[rep_short_name][0]
        else:
            citation_misses.append(citation)

    return citation_hits, citation_misses


def extract_citations(casebody_cache):
    hits, misses = extract(casebody_cache.text)
    # TODO: decide what to do with the misses
    for (citation, reporter_str) in hits.items():

        cite, created = ExtractedCitation.objects.get_or_create(original_cite=citation)
        cite.case_origins.add(casebody_cache.metadata.id)
        reporter = find_reporter_match(reporter_str)

        if not reporter:
            reporter_instances = REPORTERS[reporter_str]
            for reporter_instance in reporter_instances:
                for variation in reporter_instance['variations']:
                    reporter = find_reporter_match(variation)
                    if reporter:
                        break
        if not reporter:
            # TODO: add citation to list of misses
            return
        citation_parts = citation.split(" ")

        cite.reporter_original_string = " ".join(citation_parts[1:-1])
        cite.reporter = reporter
        cite.volume_original_number = citation_parts[0]

        try:
            cite.volume_match = VolumeMetadata.objects.get(reporter=reporter, volume_number=citation_parts[0])
        except VolumeMetadata.DoesNotExist:
            pass

        cite.page_original_number = citation_parts[-1]
        try:
            cite.citation_match = Citation.objects.get(cite=citation)
        except Citation.DoesNotExist:
            pass
        cite.save()




def find_reporter_match(reporter_str):
    try:
        reporter = Reporter.objects.get(short_name=reporter_str)
        return reporter
    except Reporter.DoesNotExist:
        return False



