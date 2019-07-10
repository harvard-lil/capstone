import copy
import random
from queue import Queue
from threading import Thread
import rocksdb
import traceback
from collections import Counter
from multiprocessing import Process, Manager
from multiprocessing.pool import Pool
import nltk
from tqdm import tqdm

from django.conf import settings

from capdb.models import Jurisdiction, CaseMetadata, CaseBodyCache
from capdb.storages import ngram_kv_store, KVDB, ngram_kv_store_ro
from scripts.helpers import ordered_query_iterator

nltk.data.path = settings.NLTK_PATH
unicode_translate_table = dict((ord(a), ord(b)) for a, b in zip(u'\u201c\u201d\u2018\u2019', u'""\'\''))

# custom tokenizer to disable separating contractions and possessives into separate words
tokenizer = copy.copy(nltk.tokenize._treebank_word_tokenizer)
tokenizer.CONTRACTIONS2 = tokenizer.CONTRACTIONS3 = []
tokenizer.ENDING_QUOTES = tokenizer.ENDING_QUOTES[:-2]

strip_chars = """`~!@#$%^&*()-_=+[{]}\|;:'",<>/?¡°¿‡†—•■"""
strip_right_chars = strip_chars + "£$©"
strip_left_chars = strip_chars + ".®"

def tokenize(text):
    # clean up input
    text = text.translate(unicode_translate_table)\
        .replace(u"\u2014", u" \u2014 ")  # add spaces around m-dashes

    # yield each valid token
    for sentence in nltk.sent_tokenize(text):
        for token in tokenizer.tokenize(sentence):
            token = token.lower().rstrip(strip_right_chars).lstrip(strip_left_chars)
            if token:
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

def get_totals_key(jurisdiction_id, year, n):
    return b"totals" + KVDB.pack((jurisdiction_id, year, n))

def ngram_jurisdictions(slug=None, max_n=3):
    """
        Add jurisdiction specified by slug to rocksdb, or all jurisdictions if name not provided.

        This is the primary ngrams entrypoint. It spawns NGRAM_THREAD_COUNT worker processes to
        ngram each jurisdiction-year, plus a rocksdb worker process that pulls their work off of
        the queue and writes it to the database.
    """
    # process pool of workers to ngram each jurisdiction-year and return keys
    ngram_workers = Pool(settings.NGRAM_THREAD_COUNT, maxtasksperchild=1)

    # inter-process queue of returned keys
    m = Manager()
    queue = m.Queue(settings.NGRAM_THREAD_COUNT)
    ngram_worker_offsets = m.dict()
    ngram_worker_lock = m.Lock()

    # process to write keys to rocksdb
    rocksdb_loaded = m.Condition()
    rocksdb_worker = Process(target=rocksdb_writer, args=(queue, rocksdb_loaded))
    rocksdb_worker.start()
    with rocksdb_loaded:
        rocksdb_loaded.wait()

    # queue each jurisdiction-year for processing
    jurisdictions = Jurisdiction.objects.all()
    if slug:
        jurisdictions = jurisdictions.filter(slug=slug)
    ngram_worker_results = []
    for jurisdiction in jurisdictions:

        # skip empty jurisdictions
        if not jurisdiction.case_metadatas.exists():
            continue

        # get year range
        case_query = CaseMetadata.objects.in_scope().filter(jurisdiction_slug=jurisdiction.slug)
        first_year = case_query.order_by('decision_date', 'id').first().decision_date.year
        last_year = case_query.order_by('-decision_date', '-id').first().decision_date.year

        # ngram each year
        for year in range(first_year, last_year + 1):
            # ngram_worker(queue, jurisdiction_id, year, max_n)
            ngram_worker_results.append((jurisdiction.slug, year, ngram_workers.apply_async(ngram_worker, (ngram_worker_offsets, ngram_worker_lock, queue, jurisdiction.id, jurisdiction.slug, year, max_n))))

    # wait for all ngram workers to finish
    ngram_workers.close()
    ngram_workers.join()

    # report failures
    for jurisdiction_slug, year, result in ngram_worker_results:
        if not result._success:
            exc = result._value
            print("%s-%s failed:" % (jurisdiction_slug, year))
            traceback.print_exception(etype=type(exc), value=exc, tb=exc.__traceback__)

    # tell rocksdb worker to exit, and wait for it to finish
    queue.put('STOP')
    rocksdb_worker.join()

def ngram_worker(ngram_worker_offsets, ngram_worker_lock, queue, jurisdiction_id, jurisdiction_slug, year, max_n):
    """
        Worker process to generate all ngrams for the given jurisdiction-year and add them to the queue.
    """
    # skip reindexing jurisdiction-year combinations that already have ngrams
    if ngram_kv_store_ro.get(get_totals_key(jurisdiction_id, year, 3)):
        return

    # tqdm setup -- add an offset based on current process index, plus space for rocksdb worker
    desc = "%s-%s" % (jurisdiction_slug, year)
    with ngram_worker_lock:
        line_offset = next((i for i in range(settings.NGRAM_THREAD_COUNT) if i not in ngram_worker_offsets), None)
        if line_offset is None:
            line_offset = random.shuffle(ngram_worker_offsets.keys())[0]
        ngram_worker_offsets[line_offset] = True
    pos = 2 + settings.NGRAM_THREAD_COUNT + line_offset

    # count words for each case
    counters = {n: {'total_tokens':0, 'total_documents':0, 'instances': Counter(), 'documents': Counter()} for n in range(1, max_n + 1)}
    queryset = CaseBodyCache.objects.filter(
        metadata__duplicative=False, metadata__jurisdiction__isnull=False, metadata__court__isnull=False,
        metadata__decision_date__year=year, metadata__jurisdiction_slug=jurisdiction_slug
    ).only('text').order_by('id')
    for case_text in tqdm(ordered_query_iterator(queryset), desc="Ngram %s" % desc, position=pos, mininterval=.5):
        tokens = list(tokenize(case_text.text))
        for n in range(1, max_n + 1):
            grams = list(' '.join(gram) for gram in ngrams(tokens, n))
            counters[n]['total_tokens'] = counters[n].setdefault('total_tokens', 0) + len(grams)
            counters[n]['total_documents'] = counters[n].setdefault('total_documents', 0) + 1
            counters[n]['instances'].update(grams)
            counters[n]['documents'].update(set(grams))

    # enqueue data for rocksdb
    storage_year = year - 1900
    for n, counts in counters.items():

        # skip storing jurisdiction-year combinations that already have ngrams
        totals_key = get_totals_key(jurisdiction_id, year, n)
        if ngram_kv_store_ro.get(totals_key):
            print(" - Length %s already in totals" % n)
            continue

        # set up values for use by rocksdb_write_thread()
        totals = (totals_key, [counts['total_tokens'], counts['total_documents']])
        merge_value_prefix = (jurisdiction_id, storage_year)

        # prepare list of all ngram observations to be merged into rocksdb, in the form:
        #   merges = [
        #     (b'<n><gram>': (<instance count>, <document count>)), ...
        #   ]
        key_prefix = bytes([int(n)])
        count_pairs = zip(sorted(counts['instances'].items()), sorted(counts['documents'].items()))
        merges = [(key_prefix+gram.encode('utf8'), (instance_count, document_count)) for (gram, instance_count), (_, document_count) in count_pairs]
        queue.put((totals, merge_value_prefix, merges))

    del ngram_worker_offsets[line_offset]

def rocksdb_writer(queue, rocksdb_loaded):
    """
        Worker process to pull ngrams off of the queue and add them to a second internal queue for writing to rocksdb.
        This spawns NGRAM_THREAD_COUNT threads to do the actual writing.
    """
    # make sure the database exists; read-only clients in ngram_worker() will choke if it doesn't
    ngram_kv_store.get(b'init')
    with rocksdb_loaded:
        rocksdb_loaded.notify_all()

    # NOTE: the following is a lower-level way to do something we could just do with multiprocessing.ThreadPool.
    # Unfortunately ThreadPool doesn't let us set a max queue size for adding tasks to the queue, which is needed for backpressure.

    # start an internal queue and threads to read from it
    internal_queue = Queue(settings.NGRAM_THREAD_COUNT)
    threads = []
    for i in range(settings.NGRAM_THREAD_COUNT):
        t = Thread(target=rocksdb_write_thread, args=(internal_queue,))
        t.start()
        threads.append(t)

    # pull all items off of the inter-process queue and onto the internal queue
    for item in tqdm(iter(queue.get, 'STOP'), position=0, desc="Jurisdiction-years written", mininterval=.5):
        internal_queue.put(item)

    # block until all tasks are done
    internal_queue.join()

    # stop worker threads
    for i in range(settings.NGRAM_THREAD_COUNT):
        internal_queue.put(None)
    for t in threads:
        t.join()

def rocksdb_write_thread(queue):
    """
        Worker thread to write ngrams to rocksdb, spawned by rocksdb_writer.
    """
    while True:
        try:
            # fetch items until 'None' is added to queue
            item = queue.get()
            if item is None:
                break
            totals, merge_value_prefix, merges = item

            # skip storing jurisdiction-year combinations that already have ngrams
            if ngram_kv_store.get(totals[0]):
                continue

            # write in a batch so writes succeed or fail as a group
            batch = rocksdb.WriteBatch()

            # write each ngram, in the form (b'<n><gram>', pack(<jurisdiction_id>, <year>, <instance_count>, <document_count>))
            # see ngram_kv_store.NgramMergeOperator for how this value is merged into the existing b'<n><gram>' key
            for k, v in tqdm(merges, desc="Current write job", mininterval=.5):
                ngram_kv_store.merge(k, merge_value_prefix+v, packed=True, batch=batch)

            # write totals value
            ngram_kv_store.put(totals[0], totals[1], packed=True, batch=batch)

            # write batch
            ngram_kv_store.db.write(batch)
        finally:
            # let internal_queue.join() know not to wait for this job to complete
            queue.task_done()
            
