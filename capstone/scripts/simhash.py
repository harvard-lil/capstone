import hashlib
import re
import simhash


# increment this whenever get_simhash() output changes, e.g. because of new tokenizer or hash function
SIMHASH_VERSION = 1


def hashfunc(obj):
    """ Return first 8 bytes of md5(obj) as an integer. """
    return int.from_bytes(hashlib.md5(obj).digest()[:8], byteorder='big')


def shingles(tokens, n):
    """
        Return n-sized shingles from a list of tokens.
        >>> assert list(shingles([1, 2, 3, 4], 2)) == [(1, 2), (2, 3), (3, 4)]
    """
    return zip(*[tokens[i:-n + i + 1 or None] for i in range(n)])


def tokenize(text):
    """
        Return text as normalized shingles -- lowercased, split on non-word characters, as 3-shingles:
        >>> assert tokenize("Hasta mañana, say we’ll meet again.") == ['hasta mañana say', 'mañana say we', 'say we ll', 'we ll meet', 'll meet again']
    """
    tokens = [t for t in re.split(r'\W+', text.lower()) if t]
    return [' '.join(s) for s in shingles(tokens, 3)]


def get_simhash(text):
    """
        Return `version:hex-encoded simhash`, based on tokenizer and hashfunc defined above.
        >>> assert get_simhash("Hasta mañana, say we’ll meet again.") == '1:f30f534aac9db398'
    """
    # Note on simhash packages: we are using the `simhash` package.
    # The `simhash-py` package is faster but the py3 version is currently unreleased. `simhash-py` version:
    # hashes = [hashfunc(s.encode('utf8')) for s in tokenize(text)]
    # value = simhash.compute(hashes)
    value = simhash.Simhash(tokenize(text), hashfunc=hashfunc).value
    return f"{SIMHASH_VERSION}:{value:016x}"


def get_distance(s1, s2):
    """
        Get Hamming distance of simhashes from get_simhash().
        >>> assert get_distance(get_simhash("This is a brown dog"), get_simhash("This is a brown doggy")) == 17
        >>> assert get_distance(get_simhash("This is a brown dog"), get_simhash("That is a brown doggy")) == 25
    """
    return simhash.Simhash(int(s1.split(':', 1)[1], 16)).distance(simhash.Simhash(int(s2.split(':', 1)[1], 16)))
    # `simhash-py` package's version:
    # return simhash.num_differing_bits(
    #     int(s1.split(':', 1)[1], 16),
    #     int(s2.split(':', 1)[1], 16))
