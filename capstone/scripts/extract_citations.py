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


def get_buckets():
    reporters = Reporter.objects.all()
    for rep in reporters:
        for vol in VolumeMetadata.objects.filter(reporter=rep):
            try:
                cases_query = CaseDocument.search().filter("term", volume_id=vol.id).sort('first_page')\
                    .source(['casebody_data.text.opinions.text', 'casebody_data.text.headmatter', 'id'])
                cases_query.aggs.bucket('vols', 'terms', field='volume.id')
                cases = cases_query.execute()
                if len(cases) > 0:
                    return cases
            except:
                pass


def extract_citations_from_casedoc(casedoc):
    casetext = ""

    if casedoc.casebody_data.text.head_matter:
        casetext += casedoc.casebody_data.text.head_matter
    for opinion in casedoc.casebody_data.text.opinions:
        casetext += opinion.text
    hits, misses = extract(casetext)
    print(hits)

    # TODO: decide what to do with the misses
    for (citation, reporter_str) in hits.items():
        print("1. matched reporter string:", citation, reporter_str)
        cite, created = ExtractedCitation.objects.get_or_create(original_cite=citation)
        print("2. extracted citation, cite:", cite, created)
        cite.case_origins.add(casedoc.id)
        cite.save()
        if created or not cite.reporter:
            reporters_to_check = []
            for rep_instance in REPORTERS[reporter_str]:
                reporters_to_check += list(rep_instance['variations'].keys())
            print("3. reporters to check:", reporters_to_check)
            reporter = find_reporter_match(reporter_str, reporters_to_check)
            print("4. matched reporter found?", reporter)
            if reporter:
                cite.reporter_match = reporter
        citation_parts = citation.split(" ")
        if created or not cite.reporter_original_string:
            cite.reporter_original_string = " ".join(citation_parts[1:-1])
        if created or not cite.volume_original_number:
            cite.volume_original_number = citation_parts[0]
        if created and reporter:
            try:
                cite.volume_match = VolumeMetadata.objects.get(
                    reporter=reporter,
                    volume_number=citation_parts[0]
                )
            except VolumeMetadata.DoesNotExist:
                pass

        cite.page_original_number = citation_parts[-1]
        try:
            cite.citation_match = Citation.objects.get(cite=citation)
        except Citation.DoesNotExist:
            pass
        cite.save()


def find_reporter_match(reporter_str, remaining_list_to_check):
    print(">>>>>>>>>>", reporter_str, remaining_list_to_check)
    try:
        reporter = Reporter.objects.get(short_name=reporter_str)
        return reporter
    except Reporter.DoesNotExist:
        # TODO: going from, potentially, least likely to most. Need to reverse!
        if len(remaining_list_to_check):
            find_reporter_match(remaining_list_to_check.pop(), remaining_list_to_check)
        else:
            return





