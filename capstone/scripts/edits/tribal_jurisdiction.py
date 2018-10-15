import logging

from capdb.models import Reporter, Court, Jurisdiction
from scripts.helpers import parse_xml, serialize_xml

logger = logging.getLogger(__name__)
info = logger.info
info = print

# One-off edit to switch jurisdictions for tribal courts appearing only in West's American Tribal Law Reporter to
# "Tribal Jurisdictions".
# See https://github.com/harvard-lil/capstone/issues/592

def make_edits(dry_run=True):
    reporter = Reporter.objects.get(full_name="West's American Tribal Law Reporter")
    new_jurisdiction = Jurisdiction.objects.get(name_long="Tribal Jurisdictions")
    courts = Court.objects.filter(case_metadatas__reporter=reporter).distinct()
    for court in courts:

        # Skip courts that have cases belonging to multiple reporters. These are federal courts
        # rather than tribal courts, which only appear in West's American Tribal Law Reporter
        if Reporter.objects.filter(case_metadatas__court=court).distinct().count() > 1:
            info("Skipping %s, has multiple reporters" % court)
            continue

        # update jurisdiction
        info("Updating jurisdiction for cases in %s" % court.name)
        if dry_run:
            info("DRY RUN: would update %s cases" % court.case_metadatas.count())
        else:
            court.jurisdiction = new_jurisdiction
            court.save()
            for case in court.case_metadatas.select_related('case_xml'):
                case_xml = case.case_xml
                parsed = parse_xml(case_xml.orig_xml)
                parsed('case|court').attr('jurisdiction', new_jurisdiction.name_long)
                case_xml.orig_xml = serialize_xml(parsed)
                case_xml.save()
