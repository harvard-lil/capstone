import copy
import json
import lzma
import tempfile
from contextlib import ExitStack, contextmanager
from heapq import merge
from collections import Counter, defaultdict
import nltk
import redis_lock
import unicodedata
from celery import shared_task
from django.conf import settings
from tqdm import tqdm

from capdb.models import Jurisdiction, CaseMetadata, CaseText
from scripts.helpers import ordered_query_iterator
from capdb.storages import ngram_storage, redis_client

nltk.data.path = settings.NLTK_PATH
unicode_translate_table = dict((ord(a), ord(b)) for a, b in zip(u'\u201c\u201d\u2018\u2019', u'""\'\''))

# custom tokenizer to disable separating contractions and possessives into separate words
tokenizer = copy.copy(nltk.tokenize._treebank_word_tokenizer)
tokenizer.CONTRACTIONS2 = tokenizer.CONTRACTIONS3 = []
tokenizer.ENDING_QUOTES = tokenizer.ENDING_QUOTES[:-2]

def has_alphanum(s):
    """
        Return True if s has at least one alphanumeric character in any language.
        See https://en.wikipedia.org/wiki/Unicode_character_property#General_Category
    """
    for c in s:
        category = unicodedata.category(c)[0]
        if category == 'L' or category == 'N':
            return True
    return False

def tokenize(text):
    # clean up input
    text = text.translate(unicode_translate_table)\
        .replace(u"\u2014", u" \u2014 ")  # add spaces around m-dashes

    # yield each valid token
    for sentence in nltk.sent_tokenize(text):
        for token in tokenizer.tokenize(sentence):
            token = token.lower().strip("'")
            if has_alphanum(token):
                yield token

def ngrams(words, n, padding=False):
    """
        Yield generator of all n-tuples from list of words.
        This approach uses more RAM but is faster than nltk.ngrams, which doesn't immediately consume the generator.
    """
    words = list(words)
    if padding:
        word_lists = [words[i:] for i in range(n)]
    else:
        word_lists = [words[i:-n+i+1 or None] for i in range(n)]
    return zip(*word_lists)

def sort_counts(counts):
    count_pairs = zip(sorted(counts['instances'].items()), sorted(counts['documents'].items()))
    for instance_count, document_count in count_pairs:
        yield (instance_count[0], str(instance_count[1]), str(document_count[1]))

@contextmanager
def get_writer_for_path(out_path):
    """
        Remove existing file at out_path, and return spooled writer that will compress written bytes and write them to
        out_path.
    """
    if ngram_storage.exists(out_path):
        ngram_storage.delete(out_path)
    with tempfile.SpooledTemporaryFile(100 * 2 ** 20) as out_raw:
        with lzma.open(out_raw, "w") as out:
            yield out
        out_raw.seek(0)
        ngram_storage.save(out_path, out_raw)

@contextmanager
def read_write_totals():
    """
        - Use a redis lock to ensure that only one process accesses totals.json at a time.
        - Read contents of totals.json and yield.
        - Save updated contents back to totals.json file.

        Example:
        >>> with read_write_totals() as totals: \
                totals['foo'] = 'bar'
    """
    lock = redis_lock.Lock(redis_client, "ngrams-totals-lock", expire=10)
    if lock.acquire(timeout=5):
        try:
            try:
                original_contents = ngram_storage.contents('totals.json')
            except FileNotFoundError:
                original_contents = "{}"
            totals = json.loads(original_contents)
            yield totals
            new_contents = json.dumps(totals, indent=4)
            if new_contents != original_contents:
                with ngram_storage.open('totals.json', 'w') as out:
                    out.write(new_contents)
        finally:
            lock.release()
    else:
        raise Exception("Failed to acquire ngrams-totals-lock within 10 seconds")

def ngram_jurisdictions(slug=None, replace_existing=False):
    """
        Call ngram_jurisdiction() for jurisdiction with given name, or all jurisdictions if name not provided.
        If replace_existing is true, will overwrite existing ngram files.
    """
    jurisdictions = Jurisdiction.objects.all()
    if slug:
        jurisdictions = jurisdictions.filter(slug=slug)
    for jurisdiction in jurisdictions:
        ngram_jurisdiction.delay(jurisdiction.pk, replace_existing)

@shared_task
def ngram_jurisdiction(jurisdiction_id, replace_existing=False, max_n=3):
    """
        For given jurisdiction, extract all ngrams up to max_n.
        Write ngrams to ngram_storage with paths like "jurisdiction_year/mass_2018-1.tsv.xz"
        Each file is an xzipped tsv with the columns "gram", "instances", and "documents"
        For each file, an entry is added to "totals.json" like:
            {
                "jurisdiction_year/mass_2018-1.tsv.xz": {
                    "grams": <gram count>,
                    "documents": <document count>
                }
            }
    """
    # get jurisdiction
    jurisdiction = Jurisdiction.objects.get(pk=jurisdiction_id)
    print("Ngramming %s" % jurisdiction)
    if not jurisdiction.case_metadatas.exists():
        print("- No cases for %s" % jurisdiction)
        return  # no cases for jurisdiction

    # get year range
    case_query = CaseMetadata.objects.in_scope().filter(jurisdiction_slug=jurisdiction.slug)
    first_year = case_query.order_by('decision_date', 'id').first().decision_date.year
    last_year = case_query.order_by('-decision_date', '-id').first().decision_date.year

    # ngram each year
    for year in range(first_year, last_year+1):

        out_stem = "jurisdiction_year/%s_%s" % (jurisdiction.slug, year)
        print("- Ngramming %s" % out_stem)

        # optionally skip reindexing jurisdiction-year combinations that already have ngrams
        if not replace_existing:
            with read_write_totals() as totals:
                if any(key.startswith(out_stem) for key in totals):
                    continue

        # count words for each case
        counters = defaultdict(lambda: defaultdict(Counter))
        queryset = CaseText.objects.filter(metadata__decision_date__year=year, metadata__jurisdiction=jurisdiction).order_by('id')
        for case_text in ordered_query_iterator(queryset):
            for n in range(1, max_n + 1):
                grams = list(' '.join(gram) for gram in ngrams(tokenize(case_text.text), n))
                counters[n]['total_tokens'] = counters[n].setdefault('total_tokens', 0) + len(grams)
                counters[n]['total_documents'] = counters[n].setdefault('total_documents', 0) + 1
                counters[n]['instances'].update(grams)
                counters[n]['documents'].update(set(grams))

        # no cases for this year
        if not counters:
            continue

        # export files
        for n, counts in counters.items():

            # write ngram file (e.g. jurisdiction_year/mass_2018-1.tsv.xz)
            out_path = out_stem + '-%s.tsv.xz' % n
            with get_writer_for_path(out_path) as out:
                out.write(bytes("gram\tinstances\tdocuments\n", 'utf8'))
                count_pairs = zip(sorted(counts['instances'].items()), sorted(counts['documents'].items()))
                for instance_count, document_count in count_pairs:
                    out.write(bytes(instance_count[0] + "\t" + str(instance_count[1]) + "\t" + str(document_count[1]) + "\n", 'utf8'))

            # add totals to totals.json file
            with read_write_totals() as totals:
                totals[out_path] = {'grams': counts['total_tokens'], 'documents': counts['total_documents']}


def merge_files(paths, out_path):
    """
        Merge a list of ngram files into a single file written to out_path.
        Each file is formatted as in ngram_jurisdiction().
        Combined total counts are written to totals.json.
    """

    # open output file for writing
    with get_writer_for_path(out_path) as out, ExitStack() as stack:

        # open all input files for reading, with lzma to remove xzip compression
        files = [
            iter(
                stack.enter_context(
                    lzma.open(
                        stack.enter_context(
                            ngram_storage.open(filename, 'rb')
            )))) for filename in paths]

        # skip header line of each input file
        for f in files:
            next(f)

        # track value of each previous line so we can combine counts
        last_gram = last_instances = last_documents = None

        # write header
        out.write(bytes("gram\tinstances\tdocuments\n", 'utf8'))

        # read sorted lines in merged order
        for line in tqdm(merge(*files)):

            gram, instances, documents = line[:-1].split(b'\t')
            instances = int(instances)
            documents = int(documents)

            # if line has same gram as previous line, merge into previous counts and move on
            if gram == last_gram:
                last_instances = last_instances + instances
                last_documents = last_documents + documents
                continue

            # write out previous line
            if last_gram:
                out.write(last_gram+b"\t"+bytes(str(last_instances), 'utf8')+b"\t"+bytes(str(last_documents), 'utf8')+b"\n")

            # start accumulating current line
            last_gram = gram
            last_instances = instances
            last_documents = documents

        # write out final line (which may have been accumulated but not written)
        out.write(last_gram+b"\t"+bytes(str(last_instances), 'utf8')+b"\t"+bytes(str(last_documents), 'utf8')+b"\n")

    # add totals to totals.json file
    with read_write_totals() as totals:
        file_totals = [totals[filename] for filename in paths]
        totals[out_path] = {
            'grams': sum(i['grams'] for i in file_totals),
            'documents': sum(i['documents'] for i in file_totals),
        }

def merge_jurisdiction_years():
    """
        Merge all ngram files in ngram_storage/jurisdiction_year/*.tsv.xz into one file per year
        Store outputs in ngram_storage/year/*.tsv.xz
    """
    # read all file names from ngram_storage/jurisdiction_year/
    paths = sorted(ngram_storage.iter_files('jurisdiction_year'))

    # parse file names and group by {'<year>-<n>': ['<path>', '<path>']}
    groups = defaultdict(list)
    for path in paths:
        if not path.endswith('.tsv.xz'):
            continue
        year_n = path.rsplit('_')[-1].split('.')[0]  # extract "2018-1" from "jurisdiction_year/mass_2018-1.tsv.xz"
        groups[year_n].append(path)

    # write merged file per year_n to ngram_storage/year/
    for year_n, paths in groups.items():
        out_path = "year/%s.tsv.xz" % year_n
        print("Merging %s files into %s" % (len(paths), out_path))
        merge_files(paths, out_path)


def merge_total():
    """
        Merge all ngram files in ngram_storage/year/*.tsv.xz into one file per ngram length
        Store outputs in ngram_storage/total/*.tsv.xz
    """
    # read all file names from ngram_storage/year/
    paths = sorted(ngram_storage.iter_files('year'))

    # parse file names and group by ngram length: {'<n>': ['<path>', '<path>']}
    groups = defaultdict(list)
    for path in paths:
        if not path.endswith('.tsv.xz'):
            continue
        n = int(path.rsplit('-')[-1].split('.')[0])
        groups[n].append(path)

    # write merged file per n to ngram_storage/total/
    for n, paths in groups.items():
        out_path = "total/total-%s.tsv.xz" % n
        print("Merging %s files into %s" % (len(paths), out_path))
        merge_files(paths, out_path)

