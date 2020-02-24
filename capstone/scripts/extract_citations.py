import re
from queue import Queue
from threading import Thread
import traceback
from multiprocessing import Process, Manager
from multiprocessing.pool import Pool
from tqdm import tqdm
from django.conf import settings

from reporters_db import REPORTERS, VARIATIONS_ONLY
from capdb.models import ExtractedCitation, Reporter, VolumeMetadata, Citation, Jurisdiction, CaseMetadata, CaseBodyCache
from scripts.helpers import ordered_query_iterator
from scripts.generate_case_html import generate_html


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


def extract_citations(casemet):
    print("extract_citations", casemet)
    try:
        casebody_cache = CaseBodyCache.objects.get(metadata=casemet)
        hits, misses = extract(casebody_cache.text)
    except CaseBodyCache.DoesNotExist:
        try:
            casebody = generate_html(casemet.case_xml.extract_casebody())
            hits, misses = extract(casebody)
        except:
            return

    # TODO: decide what to do with the misses
    for (citation, reporter_str) in hits.items():

        cite, created = ExtractedCitation.objects.get_or_create(original_cite=citation)
        print("extracted citation, cite:", cite)
        cite.case_origins.add(casemet.id)
        cite.save()
        print(cite, "exists")
        reporter = find_reporter_match(reporter_str)
        print("found reporter match", reporter)
        if not reporter:
            reporters_to_check = []
            for rep_instance in REPORTERS[reporter_str]:
                reporters_to_check += list(rep_instance['variations'].keys())
            print("reporters to check:", reporters_to_check)
            for variation in reporters_to_check:
                reporter = find_reporter_match(variation)
                if reporter:
                    print("found reporter!", reporter)
                    break


        citation_parts = citation.split(" ")

        cite.reporter_original_string = " ".join(citation_parts[1:-1])
        cite.reporter_match = reporter
        cite.volume_original_number = citation_parts[0]
        cite.save()
        try:
            cite.volume_match = VolumeMetadata.objects.get(reporter=reporter, volume_number=citation_parts[0])
        except VolumeMetadata.DoesNotExist:
            pass

        cite.page_original_number = citation_parts[-1]
        try:
            cite.citation_match = Citation.objects.get(cite=citation)
        except Citation.DoesNotExist:
            pass

def find_reporter_match(reporter_str):
    try:
        reporter = Reporter.objects.get(short_name=reporter_str)
        return reporter
    except Reporter.DoesNotExist:
        return False



