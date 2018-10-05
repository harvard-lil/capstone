import itertools
from collections import Counter
import nltk

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from capdb.models import NgramWord, CaseXML, Ngram, Jurisdiction, CaseMetadata
from scripts.helpers import extract_casebody, ordered_query_iterator


nltk.data.path = settings.NLTK_PATH
ignore_words = {
    ',', '.', '&', ';', ':', '?', '!', '``', "''",
    u'\xa7',  # section symbol
    u'\u2014'  # m-dash
}
unicode_translate_table = dict((ord(a), ord(b)) for a, b in zip(u'\u201c\u201d\u2018\u2019', u'""\'\''))

def tokenize(text):
    return (w.lower() for w in nltk.word_tokenize(
        text.translate(unicode_translate_table)
            .replace(u"\u2014", u" \u2014 ")  # add spaces around m-dashes
    ) if w not in ignore_words)

def ngrams(text, n=3):
    """ Yield all ngrams in text. Yields ("token", None, None) for tokens at end of text. """
    tokens = itertools.chain(tokenize(text), (None,) * (n-1))
    history = [next(tokens) for _ in range(n-1)]
    for i, token in enumerate(tokens):
        history.append(token)
        yield history
        history.pop(0)

def words_to_ids(ngram):
    return tuple(NgramWord.word_to_id(word) for word in ngram)

def ngram_jurisdictions(replace_existing=False):
    for jurisdiction in Jurisdiction.objects.all():
        ngram_jurisdiction.delay(jurisdiction.pk, replace_existing)

@shared_task
def ngram_jurisdiction(jurisdiction_id, replace_existing=False):
    # get jurisdiction
    jurisdiction = Jurisdiction.objects.get(pk=jurisdiction_id)
    print("Ngramming %s" % jurisdiction)
    if not jurisdiction.case_metadatas.exists():
        return  # no cases for jurisdiction

    # clear out non-existent years (which would be caused by case date change)
    case_query = CaseMetadata.objects.in_scope().filter(jurisdiction=jurisdiction)
    first_year = case_query.order_by('decision_date', 'id').first().decision_date.year
    last_year = case_query.order_by('-decision_date', '-id').first().decision_date.year
    jurisdiction.ngrams.filter(Q(year__lt=first_year) | Q(year__gt=last_year)).delete()

    # optionally skip reindexing this jurisdiction if final year already has ngrams
    if not replace_existing and Ngram.objects.filter(jurisdiction=jurisdiction, year=last_year).exists():
        return

    # ngram each year
    for year in range(first_year, last_year+1):

        # optionally skip reindexing jurisdiction-year combinations that already have ngrams
        if not replace_existing and Ngram.objects.filter(jurisdiction=jurisdiction, year=year).exists():
            continue

        # count words for each case
        # TODO: use CaseText table
        counter = Counter()
        queryset = CaseXML.objects.filter(metadata__decision_date__year=year, metadata__jurisdiction=jurisdiction).order_by('id')
        for case_xml in ordered_query_iterator(queryset):
            text = extract_casebody(case_xml.orig_xml).text()
            counter.update(words_to_ids(ngram) for ngram in ngrams(text))

        # delete existing ngrams and add new ones (if any)
        with transaction.atomic():
            jurisdiction.ngrams.filter(year=year).delete()
            if counter:
                ngram_objs = (
                    Ngram(w1_id=ngram[0], w2_id=ngram[1], w3_id=ngram[2], count=count, jurisdiction=jurisdiction, year=year)
                    for ngram, count in counter.items()
                )
                Ngram.objects.bulk_create(ngram_objs, batch_size=1000)