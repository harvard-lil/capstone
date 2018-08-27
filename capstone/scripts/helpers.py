import hashlib
import shutil
import re
from lxml import etree
from pyquery import PyQuery
from django.core.paginator import Paginator


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


def chunked_iterator(queryset, chunk_size=1000):
    """
    Avoiding holding a ton of objects in memory by paginating, yielding smaller amount of objects instead
    From https://stackoverflow.com/questions/4222176/why-is-iterating-through-a-large-django-queryset-consuming-massive-amounts-of-me/31525594#31525594
    """
    paginator = Paginator(queryset, chunk_size)
    for page in range(1, paginator.num_pages + 1):
        for obj in paginator.page(page).object_list:
            yield obj

            
def extract_casebody(case_xml):
    # strip soft hyphens from line endings
    text = case_xml.replace(u'\xad', '')
    case = parse_xml(text)

    return case('casebody|casebody')

def court_name_strip(name_text):
    name_text = re.sub('\xa0', ' ', name_text)
    name_text = re.sub('\'|’', u"\u2019", name_text)
    name_text = re.sub('\\\\', '', name_text)
    name_text = re.sub('\+', '', name_text)
    name_text = re.sub('`', '', name_text)
    name_text = re.sub(']', '', name_text)
    name_text = re.sub('0-9', '', name_text)
    name_text = re.sub('Court for The', 'Court for the', name_text)
    name_text = re.sub('Appeals[A-Za-z]', 'Appeals', name_text)
    name_text = re.sub('Pennsylvania[A-Za-z0-9\.].', 'Pennsylvania', name_text)
    return name_text

def court_abbreviation_strip(name_abbreviation_text):
    name_abbreviation_text = re.sub('\xa0', ' ', name_abbreviation_text)
    name_abbreviation_text = re.sub('\n', ' ', name_abbreviation_text)
    name_abbreviation_text = re.sub('\'|’', u"\u2019", name_abbreviation_text)
    name_abbreviation_text = re.sub('`', '', name_abbreviation_text)
    name_abbreviation_text = re.sub('^ ', '', name_abbreviation_text)
    return name_abbreviation_text

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