import json
import re
from collections import OrderedDict
from pathlib import Path
import csv
from datetime import datetime

from capdb.models import Citation, CaseMetadata, normalize_cite, EditLog


""" 
    How to run this script:
    
        * Test run: fab run_script:scripts.citation_cleanup.citation_cleanup
        * Actual run: fab run_script:scripts.citation_cleanup.citation_cleanup,dry_run=false
"""


def get_escaped_regex(string):
    return '{}'.format(re.sub(r'\\#', '[0-9]+', re.escape(string)))


def main(dry_run='true'):
    # includes all patterns to look for and how they should be modified
    with Path(__file__).parent.joinpath("modification_instructions.json").open() as fp:
        modification_instructions = json.load(fp, object_pairs_hook=OrderedDict)

    # fetch and cache citations
    print("Prefetching citations")
    all_cites = Citation.objects.filter(type="parallel").values_list('id', 'cite')

    # opens and scopes the log file handler
    with Path.home().joinpath("citation_update_logger.tsv").open("a") as logfile:

        #writes the header column on the log
        csvlog = csv.writer(logfile, delimiter='\t', quotechar='"')
        csvlog.writerow(["timestamp", "action", "New ID", "Case ID", "New Value", "Old Value", "Old ID",
                                 "Split String", "Replacement Explainer", "Filtered", "Regex Verified", "Dry Run"])

        for current_pattern, data in modification_instructions.items():
            print("Fixing %s" % current_pattern)
            modifications = data['modifications']
            jack_count = data['counts_and_examples']['count'] # the count from jack's original report
            example_cases = [pk for entry_set in data['counts_and_examples']['examples'] for pk in entry_set] #original examples
            print(example_cases)
            regex = '^' + get_escaped_regex(current_pattern) + '$' #turn the citation pattern into a regex
            matcher = re.compile(regex)
            matching_citation_ids = [id for id, cite in all_cites if matcher.match(cite)]
            matching_cite_query = Citation.objects.filter(id__in=matching_citation_ids)

            # simplify the list of example cases to make sure our search regex gets them
            example_cite_ids = []
            for epk in example_cases:
                case = CaseMetadata.objects.get(pk=epk)
                for cite in case.citations.filter(type="parallel"):
                    example_cite_ids.append(cite.pk)

            to_update = []
            to_insert = []
            to_log = []
            matching_citation_count = 0

            for matching_citation in matching_cite_query:
                matching_citation_count += 1
                csv_replacement_explainer = "" # string that will say in fairly plain english what was done
                regex_verified = [] # simple splits don't have a verification regex— it just splits and checks to make sure the output doesn't match the original pattern. I want to specify in the log if it was regex verified
                cite = matching_citation.cite
                case_id = matching_citation.case_id
                if matching_citation.pk in example_cite_ids:
                    example_cite_ids.remove(matching_citation.pk) # this list should be empty with every pattern

                # The modifications can include a split string which will split a citation up into mutiple citations,
                # 'filters' which is a list of regex substitution pairs, and "kill" which drops one section. The list orders
                # are important because they have the same indexes as the split order, so you can know where to apply what

                if 'splitstring' in modifications:
                    new_cites = [c.strip() for c in cite.split(modifications['splitstring']) if c.strip()]
                else:
                    new_cites = [cite]

                if 'filters' in modifications:
                    new_cites_filtered = []
                    filters = modifications['filters']
                    csv_replacement_explainer += "Using {} replacement".format(len(filters)) if len(filters) == 1 else "Using {} replacements".format(len(filters))
                    assert len(new_cites) == len(filters)
                    for index, (filter_dict, new_cite) in enumerate(zip(filters, new_cites)):
                        if 'kill' in filter_dict:
                            # print("Dropping {}".format(new_cite))
                            csv_replacement_explainer += ", drop split field {} ({})".format(index, new_cite)
                            continue
                        for pattern in filter_dict['patterns']:
                            csv_replacement_explainer += ", replace '{}' with '{}' in split field {} ({})".format(pattern[0], pattern[1], index, new_cite)
                            new_cite = re.sub(pattern[0], pattern[1], new_cite)
                        # The 'goal' is a pattern that the new citation should match after being processed.
                        if 'goal' in filter_dict:
                            csv_replacement_explainer += " to get '{}'".format(filter_dict['goal'])
                            regex_verified.append(new_cite)
                            if not re.match('^' + get_escaped_regex(filter_dict['goal']) + '$', new_cite):
                                raise Exception("Doesn't Match: '{}'\nCurrent Pattern:'{}'\nRegex: '{}'\nCite_Section: '{}'\n"
                                                "Goal: '{}'\nEscaped Goal: '{}'".format(
                                    cite,
                                    current_pattern,
                                    get_escaped_regex(current_pattern),
                                    new_cite,
                                    filter_dict['goal'],
                                    get_escaped_regex(filter_dict['goal'])
                                ))
                        new_cites_filtered.append(new_cite)
                    new_cites = new_cites_filtered

                # if it matches the original pattern, it's wrong
                for c in new_cites:
                    if re.match(matcher, c):
                        raise Exception("New Cite Matches Original Regex: '{}'\nCurrent Pattern:'{}'\nRegex: '{}'\n"
                                        "Cite_Section: '{}'\n".format(cite, current_pattern,
                                                                     get_escaped_regex(current_pattern), c))
                # update records and log
                for index, new_citation in enumerate(new_cites):
                    reg = True if new_citation in regex_verified else False
                    action = "update" if index == 0 else "create"
                    if action == 'update':
                        # print("Updating: {}".format(new_citation))
                        matching_citation.cite = new_citation
                        matching_citation.normalized_cite = normalize_cite(new_citation)
                        new_citation_obj = matching_citation
                        to_update.append(matching_citation)
                    elif action == 'create':
                        # print("Creating: {}".format(new_citation))
                        new_citation_obj = Citation(
                            case_id=case_id,
                            type="parallel",
                            cite=new_citation,
                            normalized_cite=normalize_cite(new_citation),
                        )
                        to_insert.append(new_citation_obj)

                    to_log.append((cite, reg, action, csv_replacement_explainer, matching_citation, new_citation_obj))

            if not to_log:
                print("- nothing to do")
                continue

            if dry_run == 'false':
                with EditLog(description='Fix citations matching %s' % current_pattern).record() as edit:
                    Citation.objects.bulk_update(to_update, ['cite', 'normalized_cite'])
                    Citation.objects.bulk_create(to_insert)
                timestamp = edit.timestamp
            else:
                timestamp = datetime.now()

            log_filters = str(modifications['filters']) if 'filters' in modifications else None
            log_splitstring = str(modifications['splitstring']) if 'splitstring' in modifications else None
            for cite, reg, action, csv_replacement_explainer, matching_citation, new_citation_obj in to_log:
                # "timestamp", "action", "New ID", "Case ID", "New Value", "Old Value", "Old ID",
                # "Split String", "Replacement Explainer", "Filtered", "Regex Verified", "Dry Run"
                csvlog.writerow([
                    timestamp, action, new_citation_obj.pk, matching_citation.case_id, new_citation_obj.cite, cite, matching_citation.pk,
                    log_splitstring, csv_replacement_explainer, log_filters, reg, dry_run,
                ])

            if matching_citation_count != jack_count:
                # This didn't happen after a dry run with production data
                print("non-matching Jack Count: {}, Query Count: {}, Pattern: {}".format(jack_count, matching_citation_count, current_pattern ))

            if len(example_cite_ids) > 0:
                # This didn't happen after a dry run with production data
                raise Exception("non-matching example in {}: {}".format(current_pattern, ", ".join(example_cite_ids)))
