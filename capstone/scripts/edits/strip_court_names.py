import re

from django.db import transaction

from capdb.models import Court
from scripts.helpers import parse_xml, serialize_xml, ordered_query_iterator


# This task applies a variety of basic normalizations to our court names -- see court_name_strip and
# court_abbreviation_strip for the changes applied.


def make_edits(dry_run=True):

    def update_cases(old_court_entry, stripped_name, stripped_abbrev, new_court_entry=None):
        query = old_court_entry.case_metadatas.order_by('id').select_related('case_xml')
        for case_metadata in ordered_query_iterator(query):
            case = case_metadata.case_xml
            parsed = parse_xml(case.orig_xml)
            parsed('case|court')[0].set("abbreviation", stripped_abbrev)
            parsed('case|court')[0].text = stripped_name
            if new_court_entry is not None:
                case_metadata.court = new_court_entry
                case_metadata.save()
            case.orig_xml = serialize_xml(parsed)
            case.save(create_or_update_metadata=False)

    for court in Court.objects.all():
        print("Checking court: %s" % court.name)
        stripped_name = court_name_strip(court.name)
        stripped_abbrev = court_abbreviation_strip(court.name_abbreviation)

        if court.name != stripped_name or court.name_abbreviation != stripped_abbrev:

            # for reporting
            diffs = []
            if court.name != stripped_name:
                diffs.append("%s -> %s" % (court.name, stripped_name))
            if court.name_abbreviation != stripped_abbrev:
                diffs.append("%s -> %s" % (court.name_abbreviation, stripped_abbrev))
            diffs = ", ".join(diffs)

            # fix each court in a transaction -- fine to start over after some courts are done
            with transaction.atomic(using='capdb'):

                # see if there are any entries which already have the correct court name/abbr/jur
                similar_court = Court.objects.order_by('slug')\
                    .filter(name=stripped_name, name_abbreviation=stripped_abbrev, jurisdiction=court.jurisdiction)\
                    .first()

                # if so, set the court entry this court's cases to the correct court, and delete this court
                # We are assuming that the first entry, organized by slug, is the correct one.
                if similar_court:
                    print("- Replacing court ID %s with %s: %s" % (court.id, similar_court.id, diffs))
                    if dry_run:
                        print("DRY RUN: Would update %s cases" % court.case_metadatas.count())
                        continue

                    update_cases(court, stripped_name, stripped_abbrev, similar_court)

                    # we delete the court once we confirm that there are no more cases associated with it
                    if len(court.case_metadatas.all()) == 0:
                        court.delete()
                    else:
                        raise Exception('{} case(s) not moved from court "{}" ("{}") to "{}" ("{}").'
                                        .format(court.case_metadatas.count(), court.name, court.name_abbreviation,
                                                similar_court.name, similar_court.name_abbreviation))

                # If there are no other similar courts, let's correct this name and cases
                else:
                    print("- Changing court ID %s: %s" % (court.id, diffs))
                    if dry_run:
                        print("DRY RUN: Would update %s cases" % court.case_metadatas.count())
                        continue

                    update_cases(court, stripped_name, stripped_abbrev)

                    # update court to match new cases
                    court.name = stripped_name
                    court.name_abbreviation = stripped_abbrev
                    court.save()

def normalize_whitespace(text):
    return re.sub(r'\s+', ' ', text).strip()

def normalize_quotes(text):
    return text.replace("’", "'")

def court_name_strip(name_text):
    name_text = normalize_whitespace(name_text)
    name_text = normalize_quotes(name_text)
    name_text = re.sub(r'[\\+`\]]', '', name_text)
    name_text = re.sub('Court for The', 'Court for the', name_text)
    name_text = re.sub('Appeals[A-Za-z]', 'Appeals', name_text)
    name_text = re.sub('Pennsylvania[A-Za-z0-9\.]', 'Pennsylvania', name_text)
    return name_text

def court_abbreviation_strip(name_abbreviation_text):
    name_abbreviation_text = normalize_whitespace(name_abbreviation_text)
    name_abbreviation_text = normalize_quotes(name_abbreviation_text)
    name_abbreviation_text = re.sub('`', '', name_abbreviation_text)
    return name_abbreviation_text