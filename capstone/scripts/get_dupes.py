import argparse
import json
import itertools
import math
import sys
import threading

from simhash import Simhash, SimhashIndex

# f1 = open('allsimhashesscasesnottexascompressed.json','r')
# f1 = open('test.json','r')

def process_hashes(input_file):
    """
        Load a list of simhashes from a JSON file with the following format:
        [
          {
            "id": 10230576,
            "hash": "1:5a9fc71ae8258ede"
          },
          {
            "id": 10231116,
            "hash": "1:2edfeeb63c80a436"
          },

        Then, output all ids for which there are less than 13 bits of difference.
        The Python `simhash` library leverages a linear-time algorithm for comparing 
        one entry against all others efficiently: http://benwhitmore.altervista.org/simhash-and-solving-the-hamming-distance-problem-explained

        To generate input file, download all `data.ljson` files from the CAP corpus and massage with the following command: cat data/data.jsonl | jq '. | {id: .id, hash: .analysis.simhash}' | jq -s | less. Watch for memory usage during jq slurp!
    """
    f1 = open(input_file,'r')

    print("Storing Hash JSON dump in memory")
    hashes = json.load(f1)

    print("Creating simhashes and index")
    simhashes = [(h["id"], Simhash(int(h["hash"].split(':')[1], 16))) for h in hashes]
    simindex = SimhashIndex(simhashes, k=13)

    print("Running get_near_dupes for each simhash")
    for obj in simhashes:
        dupes = simindex.get_near_dups(obj[1])
        if len(dupes) > 1:
            print(f"{obj[0]} similar to {dupes}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="input file containing hashes")
    args = parser.parse_args()

    process_hashes(args.file)
