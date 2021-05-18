"""
    This is a work in progress that prints the edit distance matches and standard deviations for outlier decision dates
    from https://docs.google.com/spreadsheets/d/12U_MLIGtypkIBEwmdABox2oeVrBbEIacg4eSt0_HyU8/edit#gid=1197678394 .

    It doesn't yet do anything with cases with high SDs and low edit distance; not sure if doing so would be valid.
"""
import csv
import re
from pathlib import Path
from pprint import pprint

# this requires `pip install numpy pyxDamerauLevenshtein`, which isn't included in the general project requirements
from pyxdameraulevenshtein import damerau_levenshtein_distance
import numpy as np


def get_scores(word, possibilities):
    return [[x, damerau_levenshtein_distance(word, x)] for x in possibilities]

def main():
    volume = None
    counts = {
        'matched': 0,
        'too_many': 0,
        'not_enough': 0,
        'too_close': 0,
    }
    results = []
    for row in csv.reader(Path(__file__).parent.joinpath('outlier_years.csv').open()):
        if row[0]:
            volume = {
                'barcode': row[0],
                'reporter': row[1],
                'volume': row[2],
                'sd': row[3],
                'years': [re.findall(r'\d+', year) for year in row[4].split(", ")],
            }
        elif row[5]:
            year, case_name, case_id, case_url = row[5:9]
            matches = [j[0] for j in get_scores(year, [i[0] for i in volume['years']]) if j[1] == 1]
            if len(matches) < 1:
                counts['not_enough'] += 1
                continue
            if len(matches) > 1:
                counts['too_many'] += 1
                continue
            year_int = int(year)
            if abs(year_int - int(matches[0])) < 10:
                counts['too_close'] += 1
                continue
            years = sum([[int(i[0])]*int(i[1]) for i in volume['years']], [])
            average = np.average(years)
            sd = np.std(years)
            deviations = abs(year_int-average) / sd
            # print(year, sd, deviations, matches, case_url)
            counts['matched'] += 1
            results.append([deviations, year, matches[0], case_url])
    results.sort(reverse=True)
    pprint(results)
    print(counts)

    # SD: 20?
    # edit distance: 1
    # gap more than 10 years

main()