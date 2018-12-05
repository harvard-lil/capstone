from django.db import transaction

from capdb.models import Court, CaseMetadata


# We have about 60 courts that are identical to another court. This merges those together, by updating cases
# to point to the court with the shortest slug, then deleting the duplicates.

def make_edits(dry_run=True):
    # Find all courts that have another identical court entry with a lower slug.
    duplicate_courts = list(Court.objects.raw(
        'select distinct a.* from capdb_court a, capdb_court b '
        'where a.slug>b.slug '
        'and a.name=b.name '
        'and a.name_abbreviation=b.name_abbreviation '
        'and a.jurisdiction_id=b.jurisdiction_id'))

    for court in duplicate_courts:
        print("Removing duplicate court: %s %s %s" % (court.id, court.name, court.name_abbreviation))

        # find replacement court
        replacement_court = Court.objects.filter(
            name=court.name,
            name_abbreviation=court.name_abbreviation,
            jurisdiction_id=court.jurisdiction_id
        ).order_by('slug').first()
        print("- replacing with %s %s %s" % (replacement_court.id, replacement_court.name, replacement_court.name_abbreviation))

        # update cases and delete duplicate court
        case_query = CaseMetadata.objects.filter(court=court)
        if dry_run:
            print("- would update %s cases" % case_query.count())
        else:
            with transaction.atomic(using='capdb'):
                case_query.update(court=replacement_court)
                court.delete()
