import shutil
from lxml import etree
from pyquery import PyQuery


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
    return b''.join([etree.tostring(e, encoding='utf-8', xml_declaration=True) for e in xml])

def copy_file(from_path, to_path, from_storage=None, to_storage=None):
    """
        Copy contents of from_path to to_path, optionally using storages instead of filesystem open().
    """
    from_open = from_storage.open if from_storage else open
    to_open = to_storage.open if to_storage else open
    with from_open(from_path, "rb") as in_file:
        with to_open(to_path, "wb") as out_file:
            shutil.copyfileobj(in_file, out_file)


def extract_casebody(case_xml):
    # strip soft hyphens from line endings
    text = case_xml.replace(u'\xad', '')
    case = parse_xml(text)

    # strip labels from footnotes:
    for footnote in case('casebody|footnote'):
        label = footnote.attrib.get('label')
        if label and footnote[0].text.startswith(label):
            footnote[0].text = footnote[0].text[len(label):]

    return case('casebody|casebody').html()

"""Each function in this block of functions serves as a template for some part of the data migration JSON"""
def dm_template_chg_case_content(xpath, readable_xpath, content):
    return  { "type": "non_casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "content": content }}
def dm_template_chg_casebody_content(element_id, content):
    return  { "type": "casebody", "element_id": element_id, "actions": { "content": content }}
def dm_template_chg_case_attrib(xpath, readable_xpath, attrib, value):
    return { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "attributes": { "add_update": { attrib: value }}}}
def dm_template_chg_casebody_attrib(element, attrib, value):
    return { "type": "casebody", "element_id": element, "actions": { "attributes": { "add_update": { attrib: value }}}}
def dm_template_del_case_attrib(xpath, readable_xpath, attrib):
    return { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "attributes": { "delete": [ attrib ]}}}
def dm_template_del_casebody_attrib(element, attrib, value):
    return { "type": "casebody", "element_id": element, "actions": { "attributes": { "delete": [ attrib ]}}}
def dm_template_chg_case_tag(xpath, readable_xpath, tag):
    return  { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "name": tag }}
def dm_template_chg_casebody_tag(element_id, tag):
    return  { "type": "casebody", "element_id": element_id, "actions": { "name": tag }}
def dm_template_del_case_element(xpath, readable_xpath):
    return  { "type": "non_casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "remove": True }}
def dm_template_add_case_element(xpath, parent, attribute_dict, name, content):
    return  { "type": "non_casebody", "xpath": xpath, "content": content, "name": name, "parent_xpath": parent, "actions": { "create": True, "attributes": { "add_update": attribute_dict } } }
def dm_template_del_casebody_element(element_id):
    return  { "type": "casebody", "element_id": element_id, "actions": { "remove": True }}
def dm_template_chg_alto_attrib(element, attrib, value):
    return { "type": "layout", "element": element, "actions": { "add_update": { attrib: value }}}
def dm_template_del_alto_element(element_type, element_id):
    return { "type": element_type, "element_id": element_id, "actions": { "remove": True }}

def get_alto_elements(element, parsed_case, alto_files):
    """ This gets the alto elements referred to by the casebody element"""
    
    # gets the alto file list from the case file
    alto_connections = {}
    alto_element_references = parsed_case('mets|area[BEGIN="{}"]'.format(element.get('id'))).parent().nextAll('mets|fptr')
    for area in alto_element_references('mets|area'):
        pgmap = area.get('BEGIN').split(".")[0].split("_")[1]
        alto_connections[pgmap] = (area.get('FILEID'), area.get('BEGIN'))

    # gets the alto pages referred to by the element pagemap in the case text
    element_pages = {}
    if "pgmap" in element.keys() and ' ' in element.get("pgmap"):
        element_pages = { page.split('(')[0]: page.split('(')[1][:-1] for page in element.get("pgmap").split(" ") }
    elif "pgmap" in element.keys():
        element_pages = { element.get("pgmap"): len(element.text.split(" ")) }

    for page in element_pages:
        return_map = {}
        alto_file = alto_files[alto_connections[page][0]]
        parsed_alto_file = parse_xml(alto_file.orig_xml)
        return_map['db_entry'] = alto_file
        return_map['barcode'] = alto_files[alto_connections[page][0]].barcode
        return_map['page'] = alto_connections[page][0]
        return_map['textblock'] = parsed_alto_file('alto|TextBlock[TAGREFS="{}"]'.format(element.get('id')))
        return_map['structure_tag'] = parsed_alto_file('alto|StructureTag[ID="{}"]'.format(element.get('id')))
        yield return_map

def in_casebody(element):
    """ Just checks to see if the element is in the casebody"""
    return element.tag.startswith("{" + nsmap['casebody']) and not element.tag.endswith('casebody')