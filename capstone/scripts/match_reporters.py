from collections import defaultdict
from eyecite.tokenizers import EDITIONS_LOOKUP

from capdb.models import Reporter

from scripts.helpers import group_by, alphanum_lower


### Create a mapping of eyecite Edition object -> CAP Reporter object.
# It's interesting to know this can be done but it's currently only for curiosity's sake.

def get_edition_lookup():
    # lookup of short_name -> CAP reporters by short_name
    name_to_reporter = group_by(Reporter.objects.filter(start_year__gt=0), lambda r: alphanum_lower(r.short_name))

    # lookup of eyecite Edition -> short_names (both primary and variation)
    edition_to_name = defaultdict(list)
    for k, v in EDITIONS_LOOKUP.items():
        for edition in v:
            edition_to_name[edition].append(k)

    # attempt to match each edition either by primary short_name or a variation
    edition_lookup = {}
    for edition, short_names in edition_to_name.items():
        exact_name = next(s for s in short_names if s == edition.short_name)
        variations = [s for s in short_names if s != edition.short_name]

        # if we have one match of primary short_name, use that
        exact_matches = name_to_reporter.get(alphanum_lower(exact_name), [])
        if len(exact_matches) == 1:
            edition_lookup[edition] = exact_matches[0]
            continue

        # otherwise if we have one variation match, use that
        variant_matches = set()
        for variation in variations:
            variant_matches.update(set(name_to_reporter.get(alphanum_lower(variation), [])))
        if len(variant_matches) == 1:
            edition_lookup[edition] = list(variant_matches)[0]
