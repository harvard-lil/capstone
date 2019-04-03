import hashlib
import shutil
from pathlib import Path

from django.db.models import Q
from lxml import etree
from pyquery import PyQuery

from capdb.storages import ingest_storage, private_ingest_storage

nsmap = {
    'duplicative': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body_Duplicative:v1',
    'mets': 'http://www.loc.gov/METS/',
    'case': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case:v1',
    'casebody': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1',
    'volume': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Volume:v1',
    'xlink': 'http://www.w3.org/1999/xlink',
    'alto': 'http://www.loc.gov/standards/alto/ns-v3#',
    'info': 'info:lc/xmlns/premis-v2',
}

def resolve_namespace(name):
    """
        Given a pyquery-style namespaced string like 'xlink|href', return an lxml-style namespaced string like
            '{http://www.w3.org/1999/xlink}href'
    """
    namespace, reference = name.split('|', 1)
    return '{%s}%s' % (nsmap[namespace], reference)

jurisdiction_translation = {
    '1': 'Ill.',
    'q': 'N.Y.',
    ' New York': 'N.Y.',
    'Alabama': 'Ala.',
    'Alaska': 'Alaska',
    'American Samoa': 'Am. Samoa',
    'Arizona': 'Ariz.',
    'Arkansas': 'Ark.',
    'Brooklyn': 'N.Y.',
    'Bucks': 'Pa.',
    'Buffalo': 'N.Y.',
    'Cal.': 'Cal.',
    'Califonia': 'Cal.',
    'California': 'Cal.',
    'Colorado': 'Colo.',
    'Connecticut': 'Conn.',
    'Dakota Territory': 'Dakota Territory',
    'Delaware': 'Del.',
    'District of Columbia': 'D.C.',
    'Florida': 'Fla.',
    'Georgia': 'Ga.',
    'Guam': 'Guam',
    'Hawaii': 'Haw.',
    'Idaho': 'Idaho',
    'Ill.': 'Ill.',
    'Illinois': 'Ill.',
    'Indiana': 'Ind.',
    'Iowa': 'Iowa',
    'Kansas': 'Kan.',
    'Kentucky': 'Ky.',
    'Louisiana': 'La.',
    'Maine': 'Me.',
    'Maryland': 'Md.',
    'Mass.': 'Mass.',
    'Massachusetts': 'Mass.',
    'Massachussets': 'Mass.',
    'Massachussetts': 'Mass.',
    'Michigan': 'Mich.',
    'Michigan.': 'Mich.',
    'Minnesota': 'Minn.',
    'Mississippi': 'Miss.',
    'Missouri': 'Mo.',
    'Montana': 'Mont.',
    'N.Y.': 'N.Y.',
    'Navajo': 'Navajo Nation',
    'Navajo Nation': 'Navajo Nation',
    'Nebraska': 'Neb.',
    'Nevada': 'Nev.',
    'New Hampshire': 'N.H.',
    'New Jersey': 'N.J.',
    'New Mexico': 'N.M.',
    'New York': 'N.Y.',
    'New York Court': 'N.Y.',
    'North Carolina': 'N.C.',
    'North Dakota': 'N.D.',
    'Northern Mariana Islands': 'N. Mar. I.',
    'Ohio': 'Ohio',
    'Oklahoma': 'Okla.',
    'Oregon': 'Or.',
    'Pennsylvania': 'Pa.',
    'Philadelphia': 'Pa.',
    'Puerto Rico': 'P.R.',
    'Rhode Island': 'R.I.',
    'South Carolina': 'S.C.',
    'South Dakota': 'S.D.',
    'Tennessee': 'Tenn.',
    'Texas': 'Tex.',
    'Tribal Jurisdictions': 'Tribal',
    'U. S.': 'U.S.',
    'United States': 'U.S.',
    'United Statess': 'U.S.',
    'Utah': 'Utah',
    'Vermont': 'Vt.',
    'Virgin Islands': 'V.I.',
    'Virginia': 'Va.',
    'Washington': 'Wash.',
    'West Virginia': 'W. Va.',
    'Wisconsin': 'Wis.',
    'Wyoming': 'Wyo.'
}

jurisdiction_translation_long_name = {
    'Ill.': 'Illinois',
    'N.Y.': 'New York',
    'Ala.': 'Alabama',
    'Alaska': 'Alaska',
    'Am. Samoa': 'American Samoa',
    'Ariz.': 'Arizona',
    'Ark.': 'Arkansas',
    'Pa.': 'Pennsylvania',
    'Cal.': 'California',
    'Colo.': 'Colorado',
    'Conn.': 'Connecticut',
    'Dakota Territory': 'Dakota Territory',
    'Del.': 'Delaware',
    'D.C.': 'District of Columbia',
    'Fla.': 'Florida',
    'Ga.': 'Georgia',
    'Guam': 'Guam',
    'Haw.': 'Hawaii',
    'Idaho': 'Idaho',
    'Ind.': 'Indiana',
    'Iowa': 'Iowa',
    'Kan.': 'Kansas',
    'Ky.': 'Kentucky',
    'La.': 'Louisiana',
    'Me.': 'Maine',
    'Md.': 'Maryland',
    'Mass.': 'Massachusetts',
    'Mich.': 'Michigan',
    'Minn.': 'Minnesota',
    'Miss.': 'Mississippi',
    'Mo.': 'Missouri',
    'Mont.': 'Montana',
    'Navajo': 'Navajo Nation',
    'Neb.': 'Nebraska',
    'Nev.': 'Nevada',
    'N.H.': 'New Hampshire',
    'N.J.': 'New Jersey',
    'N.M.': 'New Mexico',
    'N.C.': 'North Carolina',
    'N.D.': 'North Dakota',
    'N. Mar. I.': 'Northern Mariana Islands',
    'Ohio': 'Ohio',
    'Okla.': 'Oklahoma',
    'Or.': 'Oregon',
    'P.R.': 'Puerto Rico',
    'R.I.': 'Rhode Island',
    'S.C.': 'South Carolina',
    'S.D.': 'South Dakota',
    'Tenn.': 'Tennessee',
    'Tex.': 'Texas',
    'Tribal': 'Tribal Jurisdictions',
    'U.S.': 'United States',
    'Utah': 'Utah',
    'Vt.': 'Vermont',
    'V.I.': 'Virgin Islands',
    'Va.': 'Virginia',
    'Wash.': 'Washington',
    'W. Va.': 'West Virginia',
    'Wis.': 'Wisconsin',
    'Wyo.': 'Wyoming'
}

special_jurisdiction_cases = {
    '32044078495512': 'Ohio',
    '32044078495546': 'Ohio',
    '32044078601119': 'Cal.'
}

storage_lookup = {
    'ingest_storage': (ingest_storage, 'redacted'),
    'private_ingest_storage': (private_ingest_storage, 'unredacted'),
}


def read_file(path):
    """
        Get contents of a local file by path.
    """
    with open(path) as in_file:
        return in_file.read()


def parse_xml(xml):
    """
        Parse XML with PyQuery.
    """

    # lxml requires byte string
    if type(xml) == str:
        xml = xml.encode('utf8')

    return PyQuery(xml, parser='xml', namespaces=nsmap)


def serialize_xml(xml):
    """
        Write PyQuery object back to utf-8 bytestring.
    """
    return b''.join([etree.tostring(e, encoding='utf-8', xml_declaration=True) for e in xml]) + b'\n'


def copy_file(from_path, to_path, from_storage=None, to_storage=None):
    """
        Copy contents of from_path to to_path, optionally using storages instead of filesystem open().
    """
    from_open = from_storage.open if from_storage else open
    to_open = to_storage.open if to_storage else open
    with from_open(str(from_path), "rb") as in_file:
        with to_open(str(to_path), "wb") as out_file:
            shutil.copyfileobj(in_file, out_file)

def ordered_query_iterator(queryset, chunk_size=1000):
    """
        Run query in chunks of chunk_size.

        This requires that:
            - the query have an order_by
            - all ordering fields be null=False
            - the final ordering field be unique=True

        Alternatively you may want to use the builtin queryset.iterator(chunk_size). This function is preferable if:
            - you need prefetch_related, or
            - your database backend doesn't support server-side cursors 
             (see https://docs.djangoproject.com/en/2.1/ref/models/querysets/#iterator)
    """

    def get_filter(order_by, obj):
        """
            Get filter to return all objects coming after obj in queryset. For example,
            Given:   (('foo', 'gt'), ('bar', 'lt')), obj
            Return:  Q(foo__gt=obj.foo) | (Q(foo=obj.foo) & Q(bar__gt=obj.bar))
        """
        key_pair, *rest = order_by
        key, comparator = key_pair
        value = getattr(obj, key)
        filter = Q(**{'%s__%s' % (key, comparator): value})
        if rest:
            filter = filter | (Q(**{key: value}) & get_filter(rest, obj))
        return filter

    # get order_by fields from queryset and make sure they are valid
    order_by = queryset.query.order_by
    assert order_by, "Queryset must have a unique ordering"
    meta = queryset.model._meta
    for key in order_by:
        assert not meta.get_field(key).null, "order_by field %s must be null=False" % key
    assert meta.get_field(order_by[-1]).unique, "order_by field %s must be unique=True" % order_by[-1]
    order_by = [(key[1:], 'lt') if key.startswith('-') else (key, 'gt') for key in order_by]

    # yield each object in chunks, getting filter from final object of previous chunk
    filter = Q()
    while True:
        obj = None
        i = 0
        for obj in queryset.filter(filter)[:chunk_size]:
            yield obj
            i += 1
        if i < chunk_size:
            break
        filter = get_filter(order_by, obj)

def element_text_iter(el, with_tail=False):
    """
        Given an element, yield each (element, attr_name) pair that has text contents, in reading order.
        attr_name can be either 'text' or 'tail'.
        This is handy for processing all text within the element.

        For example, given "<p><strong><em>*</em></strong> <foo>Justice</foo></p>",
        yield (<em>, 'text'), (<strong>, 'tail'), (<foo>, 'text').
    """
    if el.text:
        yield el, 'text'
    for sub_el in el:
        for pair in element_text_iter(sub_el, True):
            yield pair
    if with_tail and el.tail:
        yield el, 'tail'

def left_strip_text(el, text):
    """
        Given an element with subelements, strip text from the left side.

        For example, given el == "<p><strong><em>*</em></strong> <strong>Justice</strong></p>", text="* JABC",
        return "<p><strong><em></em></strong><strong>ustice</strong></p>".

        Partial matches will work -- we stop removing text as soon as it stops matching.
    """
    for sub_el, text_attr in element_text_iter(el):
        # get text from target element
        new_val = getattr(sub_el, text_attr)

        # strip characters one by one while they match
        while text and new_val and text[0] == new_val[0]:
            text = text[1:]
            new_val = new_val[1:]

        # write stripped text back
        setattr(sub_el, text_attr, new_val)

        # If text is empty, we have matched all text and can stop.
        # If new_val still has text, our string has stopped matching and we can stop.
        if new_val or not text:
            break


class HashingFile:
    """ File wrapper that stores a hash of the read or written data. """
    def __init__(self, source, hash_name='md5'):
        self._sig = hashlib.new(hash_name)
        self._source = source
        self.length = 0

    def read(self, *args, **kwargs):
        result = self._source.read(*args, **kwargs)
        self.update_hash(result)
        return result

    def write(self, value, *args, **kwargs):
        self.update_hash(value)
        return self._source.write(value, *args, **kwargs)

    def update_hash(self, value):
        self._sig.update(value)
        self.length += len(value)

    def hexdigest(self):
        return self._sig.hexdigest()

    def __getattr__(self, attr):
        return getattr(self._source, attr)

def case_or_page_barcode_from_s3_key(input):
    """
        Transform s3 keys to case or page barcodes:
            32044142600386_redacted/alto/32044142600386_redacted_ALTO_00009_0.xml  ->  32044142600386_00009_0
            32044142600386_redacted/casemets/32044142600386_redacted_CASEMETS_0001.xml  -> 32044142600386_0001
    """
    if ('CASEMETS' in input or 'ALTO' in input) and input.endswith("xml"):
        return input.split('/')[-1].split('.')[0]\
            .replace('unredacted', 'redacted')\
            .replace('_redacted_ALTO', '')\
            .replace('_redacted_CASEMETS', '')
    raise Exception("Not an ALTO or CASEMETS s3_key")

def short_id_from_s3_key(input):
    """
        Transform s3 keys to case or page short IDs used by volume XML:
            32044142600386_redacted/alto/32044142600386_redacted_ALTO_00009_0.xml  ->  alto_00009_0
            32044142600386_redacted/casemets/32044142600386_redacted_CASEMETS_0001.xml  -> casemets_0001
    """
    if ('CASEMETS' in input or 'ALTO' in input) and input.endswith("xml"):
        return input.split('/')[-1].split('.')[0].split('redacted_')[1].lower()
    raise Exception("Not an ALTO or CASEMETS s3_key")

def volume_barcode_from_folder(folder):
    """
        Transform folder name to barcode:
            Cal4th_063_redacted  ->  Cal4th_063
            32044032501660_unredacted_2018_10_18_06.26.00  ->  32044032501660
    """
    return folder.replace('unredacted', 'redacted').split("_redacted", 1)[0]

def up_to_date_volumes(volume_paths):
    """ Get all up-to-date volumes from a list of paths. Yields (volume_barcode, path) for each up-to-date path. """
    current_vol = next(volume_paths, "")
    while current_vol:
        next_vol = next(volume_paths, "")
        if volume_barcode_from_folder(Path(current_vol).name) != volume_barcode_from_folder(Path(next_vol).name):
            yield (volume_barcode_from_folder(Path(current_vol).name), Path(current_vol))
        current_vol = next_vol