import copy
import nltk

from django.conf import settings


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


def ngrams(words, n):
    """
        Yield generator of all n-tuples from list of words.
        This approach uses more RAM but is faster than nltk.ngrams, which doesn't immediately consume the generator.
    """
    words = list(words)
    word_lists = [words[i:-n+i+1 or None] for i in range(n)]
    return zip(*word_lists)