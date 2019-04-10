import csv
import re
from functools import lru_cache
from pathlib import Path

"""
    The original court tag in our XML looks like this:
        <court abbreviation="Ill." jurisdiction="Illinois">Illinois Supreme Court</court>
    
    The tag does not follow a defined dictionary of court names, and requires a variety of cleanup that happens here:
        (a) Strip whitespace and normalize smart quotes.
        (b) Apply custom transformations specified in .csv files.
        
    The .csv files specify a Court ID, which is arbitrary, and a set of transformations:
        Court Name -> Fixed Court Name
        Court Name Abbreviation -> Fixed Court Name Abbreviation
        Jurisdiction -> Fixed Jurisdiction
    If 'Fixed Court Name' is numeric, it is assumed to be a Court ID, and all 'Fixed' values are pulled from the
    referenced row.
    
    Documentation of .csv files:
        * tribal_jurisdiction.csv changes certain courts from West's American Tribal Law Reporter to have jurisdiction
            'Tribal Jurisdictions' instead of 'United States'. Courts included are those that don't appear in any other
            reporter. See https://github.com/harvard-lil/capstone/issues/592
        * manual_fixes.csv is exported from the "Court Names" spreadsheet in our "Data updates" Google folder. It was
            originally created with this SQL:
                \copy (SELECT ct.id, ct.name, ct.name_abbreviation, COUNT(cs.id), j.name, MIN(cs.decision_date), 
                MAX(cs.decision_date), MIN(cs.id) FROM capdb_court ct, capdb_jurisdiction j, capdb_casemetadata cs 
                WHERE cs.court_id=ct.id AND ct.jurisdiction_id=j.id GROUP BY ct.id, j.id) To '/home/jcushman/courts.csv' 
                With CSV 
            and manually filled in by Adam and Jack in March 2019.
    
"""


def fix_court_tag(jurisdiction_name, court_name, court_abbrev):
    """
        Main function to translate
            old_jurisdiction, old_court_name, old_abbreviation
        to
            (new_jurisdiction, new_court_name, new_abbreviation)
    """
    # normalize whitespace etc.
    court_name = court_name_strip(court_name)
    court_abbrev = court_abbreviation_strip(court_abbrev)

    # repeatedly correct values from normalizations() dict (function call is cached, so dict is only loaded once)
    key = (jurisdiction_name, court_name, court_abbrev)
    prev_keys = {key}
    while key in normalizations():
        key = normalizations()[key]

        # avoid infinite loops
        if key in prev_keys:
            break
        prev_keys.add(key)

    return key

@lru_cache(None)
def normalizations():
    """
        Load .csv files from the fix_court_tag directory, and return a mapping of
            (old_jurisdiction, old_court_name, old_abbreviation) -> (new_jurisdiction, new_court_name, new_abbreviation)
    """

    # get a fixed version of a given line of a csv
    def fixed(line):
        return (
            line['Fixed Jurisdiction'] or line['Jurisdiction'],
            line['Fixed Court Name'] or line['Court Name'],
            line['Fixed Court Name Abbreviation'] or line['Court Name Abbreviation'],
        )

    # read lines of each csv
    to_fix = {}
    for path in Path(__file__).parent.glob('*.csv'):
        with path.open() as in_file:
            reader = csv.DictReader(in_file)
            lines_by_id = {line['Court ID']:line for line in reader}

        for line in lines_by_id.values():
            key = (line['Jurisdiction'], line['Court Name'], line['Court Name Abbreviation'])

            # sometimes a number is accidentally put in the wrong column:
            if line['Fixed Court Name Abbreviation'].isdigit():
                line['Fixed Court Name'] = line['Fixed Court Name Abbreviation']

            # if 'Fixed Court Name' is numeric, look up corrected value from referenced Court ID:
            if line['Fixed Court Name'].isdigit():
                if line['Fixed Court Name'] == line['Court ID']:
                    raise ValueError("Court %s cannot have itself as reference." % line['Court ID'])
                new_line = lines_by_id[line['Fixed Court Name']]
                line_ids = {line['Court ID'], new_line['Court ID']}
                while new_line['Fixed Court Name'].isdigit():
                    new_line = lines_by_id[new_line['Fixed Court Name']]
                    if new_line['Court ID'] in line_ids:
                        raise ValueError("Court list %s is a reference loop" % line_ids)
                    line_ids.add(new_line['Court ID'])
                to_fix[key] = fixed(new_line)

            # else fill in corrections directly, if any:
            else:
                fixed_line = fixed(line)
                if fixed_line != key:
                    to_fix[key] = fixed_line

    return to_fix

### whitespace normalizations ###

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

