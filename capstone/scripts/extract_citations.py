import re
from capapi.documents import CaseDocument
from reporters_db import REPORTERS, VARIATIONS_ONLY
from capdb.models import ExtractedCitation, Reporter, VolumeMetadata, Citation, Jurisdiction, CaseMetadata, CaseBodyCache


def extract(case_text):
    """
    Takes case text and returns two lists:
    a dict of citations that we think exist set to likely reporters
    and a list of strings that look like citations but don't match reporters
    """
    results = re.finditer(r"((?:\d\.?\s?)+)\s+([0-9a-zA-Z][\s0-9a-zA-Z.']{0,40})\s+(\d+)", case_text)
    citation_hits = {}
    citation_misses = []
    for result in results:
        vol_num, rep_short_name, page_num = result.groups()
        citation = result.group()
        if rep_short_name in REPORTERS:
            # check if exists as official or variation name
            citation_hits[citation] = {"reporter": rep_short_name, "reporter_original_string": rep_short_name,
                                       "vol_num": vol_num, "page_num": page_num}
        elif rep_short_name in VARIATIONS_ONLY:
            citation_hits[citation] = {"reporter": VARIATIONS_ONLY[rep_short_name][0],
                                       "reporter_original_string": rep_short_name, "vol_num": vol_num,
                                       "page_num": page_num}
        else:
            citation_misses.append(citation)
    print("extract, hits:", len(citation_hits.keys()), len(citation_misses))
    return citation_hits, citation_misses


def extract_citations_from_casedoc(casedoc, volume_id, update_existing=False):
    casetext = ""

    if casedoc.casebody_data.text.head_matter:
        casetext += casedoc.casebody_data.text.head_matter
    for opinion in casedoc.casebody_data.text.opinions:
        casetext += opinion.text
    hits, misses = extract(casetext)

    # TODO: decide what to do with the misses
    for citation, cite_parts in hits.items():
        reporter_str = cite_parts["reporter"]
        cite, created = ExtractedCitation.objects.get_or_create(original_cite=citation)
        cite.case_origins.add(casedoc.id)
        if created or update_existing:
            reporters_to_check = []
            for rep_instance in REPORTERS[reporter_str]:
                reporters_to_check += list(rep_instance['variations'].keys())
            reporter = find_reporter_match(reporter_str, reporters_to_check)
            if reporter:
                cite.reporter_match = reporter
                try:
                    cite.volume_match = VolumeMetadata.objects.get(
                        reporter=reporter,
                        volume_number=cite_parts["vol_num"]
                    )
                except VolumeMetadata.DoesNotExist:
                    pass

            cite.reporter_original_string = cite_parts["reporter_original_string"]
            cite.volume_original_number = cite_parts["vol_num"]
            cite.save()
            cite.page_original_number = cite_parts["page_num"]
            try:
                cite.citation_match = Citation.objects.get(cite=citation)
            except Citation.DoesNotExist:
                pass
            cite.save()


def find_reporter_match(reporter_str, remaining_list_to_check):
    # print(">>>>>>>>>>", reporter_str, remaining_list_to_check)
    try:
        reporter = Reporter.objects.get(short_name=reporter_str)
        return reporter
    except Reporter.DoesNotExist:
        # TODO: going from, potentially, least likely to most. Need to reverse!
        if len(remaining_list_to_check):
            find_reporter_match(remaining_list_to_check.pop(), remaining_list_to_check)
        else:
            return





