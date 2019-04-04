import bisect
import json
import re
import shutil
import subprocess
import tempfile
from base64 import b64encode
from copy import deepcopy
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
from PIL import Image
from celery import shared_task
from diff_match_patch import diff_match_patch
from lxml import etree

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from capdb.models import CaseFont, PageStructure, VolumeMetadata, CaseMetadata, CaseStructure, Reporter, \
    CaseInitialMetadata, CaseXML, TarFile
from capdb.storages import captar_storage, CapS3Storage
from scripts import render_case
from scripts.compress_volumes import files_by_type, open_captar_volume
from scripts.helpers import parse_xml



### HELPERS ###
from scripts.render_case import iter_pars

rect_attrs = ['HPOS', 'VPOS', 'WIDTH', 'HEIGHT']
def rect(el_attrib):
    """ Convert an XML element like <foo HPOS="1" VPOS="2" WIDTH="3" HEIGHT="4"> to [1, 2, 3, 4]. """
    return [float(el_attrib[attr]) if '.' in el_attrib[attr] else int(el_attrib[attr]) for attr in rect_attrs]

def parse(storage, path, remove_namespaces=True):
    """ Extract .gz-compressed XML path from storage, and return as PyQuery object. """
    xml = parse_xml(storage.contents(path[:-3]))  # strip .gz so captar_storage will decompress for us
    if remove_namespaces:
        xml = xml.remove_namespaces()
    return xml

def diff_strings(text1, text2):
    """
        Return a diff from text1 to text2, in the format used by difflib.
        Internally this currently uses diff_match_patch, which provides better minimal diffs.
        Example:
            >>> blocks_text = "1234a5678a1234b5678"
            >>> case_text = "1234c5678c12345678d"
            >>> diff_strings(blocks_text, case_text)
            [('equal', 0, 4, 0, 4),
             ('replace', 4, 5, 4, 5),
             ('equal', 5, 9, 5, 9),
             ('replace', 9, 10, 9, 10),
             ('equal', 10, 14, 10, 14),
             ('delete', 14, 15, 14, 14),
             ('equal', 15, 19, 14, 18),
             ('insert', 19, 19, 18, 19)]
            >>> diff_strings(blocks_text, case_text) == difflib.SequenceMatcher(None, text1, text2).get_opcodes()
            True
    """
    # get diff
    diff = diff_match_patch().diff_main(text1, text2)

    # convert to difflib format
    opcodes = []
    i = 0
    j = 0
    for opcode, text in diff:
        text_length = len(text)
        if opcode == diff_match_patch.DIFF_EQUAL:
            opcodes.append(('equal', i, i+text_length, j, j+text_length))
            i += text_length
            j += text_length
        elif opcode == diff_match_patch.DIFF_DELETE:
            opcodes.append(('delete', i, i+text_length, j, j))
            i += text_length
        elif opcode == diff_match_patch.DIFF_INSERT:
            if opcodes and opcodes[-1][0] == 'delete':
                prev = opcodes.pop()
                opcodes.append(('replace', prev[1], prev[2], j, j+text_length))
            else:
                opcodes.append(('insert', i, i, j, j+text_length))
            j += text_length
    return opcodes

def tokenize_element(parent):
    """
        Tokenize the contents of an lxml Element. Example:
        >>> tokenize_element(etree.XML("<p>text <footnotemark ref='foo'>1</footnotemark> text</p>"))
        ['text ', ['footnotemark', {'ref':'foo'}], '1', ['/footnotemark'], ' text']
    """
    yield parent.text
    for el in parent:
        yield [el.tag] + ([dict(el.attrib)] if el.attrib else [])
        yield from tokenize_element(el)
        yield ['/'+el.tag]
        yield el.tail

def insert_tags(block, i, offset, new_tokens):
    """
        Insert new tokens at a given offset in a given string inside a list of strings.
        Return change in length of block.
        Example:
        >>> block = ['foo', 'bar']
        >>> insert_tags(block, 1, 2, [['new'], ['stuff']])
        3
        >>> blocks
        ['foo', 'ba', ['new'], ['stuff'], 'r']
    """
    text = block[i]
    to_insert = [token for token in [text[:offset]]+new_tokens+[text[offset:]] if token]
    block[i:i + 1] = to_insert
    return len(to_insert) - 1

def index_blocks(blocks):
    """
        Given a list of blocks, return:
            (a) the combined text from the blocks
            (b) the offsets mapping from that text back to each string in the blocks
            (c) a lookup of the strings themselves
        Example:
            >>> blocks = [['foo', ['tag'], 'bar'], ['baz']]
            >>> blocks_text, blocks_offsets, blocks_lookup = index_blocks(blocks)
            >>> blocks_text
            'foobarbaz'
            >>> blocks_offsets
            [0, 3, 6]
            >>> blocks_lookup
            [[0, ['foo', ['tag'], 'bar'], 0], [3, ['foo', ['tag'], 'bar'], 2], [6, ['baz'], 0]]
        This allows us to start from the combined text and use it to modify the individual strings in the blocks object.
        For example, if we want to modify blocks_text[5] (an 'r'), we can search blocks_offsets to figure out that it is part
        of entry 1 (because it is after 3 and before 6), and then use blocks_lookup[1] to update the original string.
    """
    blocks_text = ''
    blocks_offsets = []
    blocks_lookup = []
    for block in blocks:
        for i, token in enumerate(block):
            if type(token) == str:
                blocks_offsets.append(len(blocks_text))
                blocks_lookup.append((len(blocks_text), block, i))
                blocks_text += token
    return blocks_text, blocks_offsets, blocks_lookup

def sync_alto_blocks_with_case_tokens(alto_blocks, case_tokens):
    """
        Given a list of blocks of tokens from ALTO, and a single tokenized paragraph from CaseMETS, add 'edit' tags to
        make the ALTO text match the case text. Then import all tags from the CaseMETS (such as footnotemark) into the
        ALTO. Example:
            >>> alto_blocks = [[["baz"], "abc-", "def"], ["gh-i", "jkl", ["/baz"]]]
            >>> case_tokens = [["bar"], "abcd", ["foo"], "efg", ['/foo'], "hijkl", ["/bar"]]
            >>> sync_alto_blocks_with_case_tokens(alto_blocks, case_tokens)
            >>> blocks
            [[['baz'], ['bar'], 'abc', ['edit', {'was': '-'}], ['/edit'], 'd', ['foo'], 'ef'], [['edit', {'was': '-'}], ['/edit'], 'g', ['/foo'], 'hi', 'jkl', ['/bar'], ['/baz']]]
    """

    ## initial indexing ##

    # Break out the new tokens into a list of non-text tokens in [offset, token] form, and a string of the text tokens
    case_tags = []
    case_text = ""
    for token in case_tokens:
        if type(token) == str:
            if not case_text:
                case_text += token.lstrip()  # lstrip here so offsets will be correct
            else:
                case_text += token
        else:
            case_tags.append([len(case_text), token])
    case_text = case_text.rstrip()  # remove any whitespace at start and end of paragraph of case text

    blocks_text, blocks_offsets, blocks_lookup = index_blocks(alto_blocks)

    ## text update -- update ALTO text to match case text ##

    if case_text != blocks_text:

        # Get all differences between alto text and case text,
        # in order from end to start so we don't mess up indexes as we make edits.
        # tag will be "insert", "replace", or "delete"
        # i1:i2 will be the target range in the alto text, and j1:j2 will be the source range in the case text
        for tag, i1, i2, j1, j2 in reversed(diff_strings(blocks_text, case_text)):
            if tag == 'equal':
                continue

            # find the target block for this edit
            block_index = bisect.bisect_right(blocks_offsets, i1) - 1
            offset, block, i = blocks_lookup[block_index]

            # update range relative to offset for this block
            i1 -= offset
            i2 -= offset

            # remove text from block, if necessary
            len_to_remove = i2-i1
            if len_to_remove:
                # tag == "replace" or "delete"
                removed = block[i][i1:i2]
                block[i] = block[i][:i1] + block[i][i2:]
            else:
                # tag == "insert"
                removed = ''

            # replace removed text with new text from case text, if any
            insert_count = insert_tags(block, i, i1, [
                ['edit', {'was': removed}],
                case_text[j1:j2],  # will be empty if tag == "delete"
                ['/edit'],
            ])

            # if we still have more text to delete, keep removing it from subsequent block-strings
            len_to_remove -= len(removed)
            while len_to_remove > 0:

                # find next block-string
                old_block = block
                block_index += 1
                offset, block, i = blocks_lookup[block_index]

                # modify block-string index based on any items we've already inserted into this block
                if block != old_block:
                    insert_count = 0
                i += insert_count

                # delete text
                removed = block[i][:len_to_remove]
                block[i] = block[i][len_to_remove:]
                insert_count += insert_tags(block, i, 0, [
                    ['edit', {'was': removed}],
                    ['/edit'],
                ])
                len_to_remove -= len(removed)

        # reindex blocks to account for edits
        blocks_text, blocks_offsets, blocks_lookup = index_blocks(alto_blocks)

    # insert all case_tokens into blocks
    for position, token in reversed(case_tags):
        offset, block, i = blocks_lookup[bisect.bisect_right(blocks_offsets, position)-1]
        insert_tags(block, i, position - offset, [token])

def sync_alto_blocks_with_case_paragraphs(pars, blocks_by_id, case_id_to_alto_ids):
    """
        Given a list of CaseMETS paragraphs as PyQuery objects, update all ALTO blocks in blocks_by_id that are
        referenced by those paragraphs. We make two kinds of updates:
            (a) last block in paragraph should not have a space at the end
            (b) blocks get their text and tags updated based on case text and tags (e.g. hyphen fixes, footnotemarks)
    """
    for par in pars:
        # look up ALTO blocks from case paragraph IDs
        alto_ids = case_id_to_alto_ids[par.attr.id]
        blocks = [blocks_by_id[id]['tokens'] for id in alto_ids if blocks_by_id[id].get('tokens')]
        if not blocks:
            continue

        # remove space from end of final block in paragraph
        last_block = blocks[-1]
        for i in range(len(last_block)-1, -1, -1):
            if type(last_block[i]) == str:
                last_block[i] = last_block[i].rstrip()
                break

        # sync text and tags
        sync_alto_blocks_with_case_tokens(blocks, tokenize_element(par[0]))

def extract_paragraphs(children, case_id_to_alto_ids, blocks_by_id):
    """
        Extract paragraph and footnote structures from a list of CaseMETS paragraphs and footnotes as PyQuery elements.
        Example:
            >>> children = PyQuery("<opinion><author id='1'>text</author><footnote id='footnote_1_1'><p id='2'>footnote text</p></footnote></opinion>").children().items()
            >>> paragraphs, footnotes, paragraph_els = extract_paragraphs(children, case_id_to_alto_ids, blocks_by_id)
            >>> paragraphs
            [{'id': 1, 'class': 'author', 'block_ids':[1]}]
            >>> footnotes
            [{'id': 'footnote_1_1', 'paragraphs': [{'id': 2, 'class': 'p', 'block_ids':[2, 3]}]
            >>> paragraph_els
            [<PyQuery ...>, <PyQuery ...>]
    """
    paragraphs = []
    footnotes = []
    paragraph_els = []
    for el in children:
        if el[0].tag == 'footnote':
            # extract footnote tag and call self recursively to get footnote paragraphs
            footnote = {'id': el.attr.id}
            if el.attr.label:
                footnote['label'] = el.attr.label
            if el.attr.redact:
                footnote['redacted'] = el.attr.redact == 'true'
            if el.attr.orphan:
                footnote['orphan'] = el.attr.orphan
            footnote_pars, _, footnote_par_els = extract_paragraphs(el.children().items(), case_id_to_alto_ids, blocks_by_id)

            # casemets <footnote redact='true'> flag is not reliably set. we also set it if all paragraphs are redacted.
            if all(par.get('redacted', False) for par in footnote_pars):
                footnote['redacted'] = True

            footnote['paragraphs'] = footnote_pars
            paragraph_els.extend(footnote_par_els)
            footnotes.append(footnote)
        else:
            # extract other tags as paragraphs
            par = {
                'id': el.attr.id,
                'class': el[0].tag,
                'block_ids': case_id_to_alto_ids[el.attr.id],
            }
            if all(blocks_by_id[id].get('redacted', False) for id in par['block_ids']):
                par['redacted'] = True
            paragraphs.append(par)
            paragraph_els.append(el)
    return paragraphs, footnotes, paragraph_els

def xml_strings_equal(s1, s2, ignore={}):
    """
        Raise ValueError if xml strings do not represent equivalent XML, ignoring linebreaks (but not whitespace) between elements.
        ignore is a dictionary of tags, attributes, or tag attributes that should be ignored when comparing.
    """
    s1 = re.sub(r'>\s*\n\s*<', '><', s1, flags=re.S)
    s2 = re.sub(r'>\s*\n\s*<', '><', s2, flags=re.S)
    e1 = etree.fromstring(s1)
    e2 = etree.fromstring(s2)
    return elements_equal(e1, e2, ignore)

def elements_equal(e1, e2, ignore={}):
    """
        Recursively compare two lxml Elements. Raise ValueError if not identical.
    """
    if e1.tag != e2.tag:
        raise ValueError("e1.tag != e2.tag (%s != %s)" % (e1.tag, e2.tag))
    if e1.text != e2.text:
        raise ValueError("e1.text != e2.text (%s != %s)" % (e1.text, e2.text))
    if e1.tail != e2.tail:
        raise ValueError("e1.tail != e2.tail (%s != %s)" % (e1.tail, e2.tail))
    ignore_attrs = ignore.get('attrs', set()) | ignore.get('tag_attrs', {}).get(e1.tag.rsplit('}', 1)[-1], set())
    e1_attrib = {k:v for k,v in e1.attrib.items() if k not in ignore_attrs}
    e2_attrib = {k:v for k,v in e2.attrib.items() if k not in ignore_attrs}
    if e1_attrib != e2_attrib:
        raise ValueError("e1.attrib != e2.attrib (%s != %s)" % (e1_attrib, e2_attrib))
    s1 = [i for i in e1 if i.tag.rsplit('}', 1)[-1] not in ignore.get('tags', ())]
    s2 = [i for i in e2 if i.tag.rsplit('}', 1)[-1] not in ignore.get('tags', ())]
    if len(s1) != len(s2):
        raise ValueError("e1 children != e2 children (%s != %s)" % (s1, s2))
    for c1, c2 in zip(s1, s2):
        elements_equal(c1, c2, ignore)

def create_page_obj(volume_obj, page, ingest_source=None):
    """
        Convert a page dict into a PageStructure object.
    """
    return PageStructure(
        volume=volume_obj,
        order=page['order'],
        label=page['label'],
        blocks=page['blocks'],
        spaces=page['spaces'] or None,
        encrypted_strings=page.get('encrypted_strings') or None,
        image_file_name=page['file_name'],
        width=page['width'],
        height=page['height'],
        deskew=page['deskew'],
        font_names=page['font_names'],
        ingest_source=ingest_source,
        ingest_path=page['path'],
    )


@shared_task
def volume_to_json(volume_barcode, primary_path, secondary_path, key=settings.REDACTION_KEY, save_failed=False):
    """
        Given volume barcode and locations of redacted and unredacted captar files, write out extracted tokenstreams
        as a zip file. This wrapper just makes sure the captar files are available locally, and then hands off to
        another function for the main work.
    """
    unredacted_storage = redacted_storage = None
    try:
        with open_captar_volume(Path(primary_path), False) as unredacted_storage:
            if secondary_path:
                with open_captar_volume(Path(secondary_path), False) as redacted_storage:
                    volume_to_json_inner(volume_barcode, unredacted_storage, redacted_storage, key=key)
            else:
                volume_to_json_inner(volume_barcode, unredacted_storage, key=key)
    except:
        if isinstance(captar_storage, CapS3Storage):
            # copy busted S3 files locally for further inspection
            for storage in (unredacted_storage, redacted_storage):
                if not storage:
                    continue
                if save_failed:
                    dest_dir = Path(settings.BASE_DIR, 'test_data/zips')
                    print("Copying failed captar from %s to %s" % (storage.parent.location, dest_dir))
                    subprocess.call(['rsync', '-a', storage.parent.location + '/', str(dest_dir)])
                shutil.rmtree(storage.parent.location)  # delete local temp dir
        raise


def volume_to_json_inner(volume_barcode, unredacted_storage, redacted_storage=None, key=settings.REDACTION_KEY):
    """
        Given volume barcode and redacted and unredacted captar storages, write out extracted tokenstreams as a zip file.
    """
    
    pages = []
    cases = []
    fonts = {}
    paths = files_by_type(sorted(unredacted_storage.iter_files_recursive()))

    ### Extract data from volmets into volume dict ###

    print("Reading volmets")
    parsed = parse(unredacted_storage, paths['volume'][0])
    volume_el = parsed('volume')
    volume = {
        'barcode': volume_el.attr.barcode,
        'page_labels': {int(item.attr.ORDER): item.attr.ORDERLABEL for item in parsed('structMap[TYPE="physical"] div[TYPE="volume"] div[TYPE="page"]').items()},
    }
    metadata = volume['metadata'] = {
        'start_date': volume_el('voldate start').text(),
        'end_date': volume_el('voldate end').text(),
        'spine_start_date': volume_el('spinedate start').text(),
        'spine_end_date': volume_el('spinedate end').text(),
        'publication_date': volume_el('publicationdate').text(),
        'tar_path': str(unredacted_storage.path),
        'tar_hash': unredacted_storage.get_hash(),
        'contributing_library': volume_el.attr.contributinglibrary,
    }
    reporter_el = volume_el('reporter')
    metadata['reporter'] = {
        'name': reporter_el.text(),
        'abbreviation': reporter_el.attr.abbreviation,
        'volume_number': reporter_el.attr.volnumber,
    }
    nominative_reporters = [{
        'name': reporter_el.text(),
        'abbreviation': reporter_el.attr.abbreviation,
        'volume_number': reporter_el.attr.volnumber,
    } for reporter_el in volume_el('nominativereporter').items() if (
        reporter_el.text() or reporter_el.attr.abbreviation or reporter_el.attr.volnumber
    )]
    if nominative_reporters:
        metadata['nominative_reporters'] = nominative_reporters
    publisher_el = volume_el('publisher')
    metadata['publisher'] = {
        'name': publisher_el.text(),
        'place': publisher_el.attr.place,
    }

    ### Extract data for each page into the pages dict ###

    print("Reading ALTO files")
    fake_font_id = 1
    fonts_by_id = {}
    for path in paths['alto']:
        print(path)

        parsed = parse(unredacted_storage, path)
        alto_id = 'alto_' + path.split('_ALTO_', 1)[1].split('.')[0]

        # load redacted file and determine which IDs appear in the redacted version
        if redacted_storage:
            redacted_parsed = parse(redacted_storage, path.replace('unredacted', 'redacted'))
            unredacted_block_ids = {block.attr.ID for block in redacted_parsed('TextBlock,Illustration').items()}
            unredacted_string_ids = {block.attr.ID for block in redacted_parsed('String').items()}

        # build lookup of block labels (e.g. name, p, blockquote) by tagref ID
        labels_by_tagref = {s.attrib['ID']: s.attrib['LABEL'] for s in parsed[0].iter('StructureTag')}  #

        page_el = parsed('Page')
        page = {
            'id': alto_id,
            'path': str(path),
            'order': int(page_el.attr.ID.split("_")[1]),
            'width': int(page_el.attr.WIDTH),
            'height': int(page_el.attr.HEIGHT),
            'file_name': parsed('sourceImageInformation fileName').text().replace('.png', '.tif'),
            'deskew': parsed('processingStepSettings').text(),
            'spaces': [],
            'blocks': [],
        }

        # look up page label from volume info
        page['label'] = volume['page_labels'][page['order']]

        # build a lookup of CaseFont objects by alto style ID
        fonts_by_style_id = {}
        for s in parsed[0].iter('TextStyle'):
            font = (s.attrib['FONTFAMILY'], s.attrib['FONTSIZE'], s.attrib.get('FONTSTYLE', ''), s.attrib['FONTTYPE'], s.attrib['FONTWIDTH'])
            if font in fonts:
                font_id = fonts[font]
            else:
                font_obj = CaseFont(pk=fake_font_id, family=font[0], size=font[1], style=font[2], type=font[3], width=font[4])
                fake_font_id += 1
                font_id = fonts[font] = font_obj.pk
                fonts_by_id[font_id] = font_obj
            fonts_by_style_id[s.attrib['ID']] = font_id

        # store an CaseFont ID -> alto style ID mapping so we can regenerate the ALTO for testing
        page['font_names'] = {v:k for k, v in fonts_by_style_id.items()}

        # ALTO files are structured like:
        # <Page>
        #   <PrintSpace>
        #       <Illustration/>
        #       <TextBlock>
        #           <TextLine>
        #               <String/>
        # This nested loop steps through that structure:
        for space_el in page_el('PrintSpace').items():

            # <PrintSpace> mostly seems to be redundant of <Page>, but store it if it's not redundant:
            space_rect = rect(space_el[0].attrib)
            if space_rect == [0, 0, page['width'], page['height']]:
                space_index = None
            else:
                page['spaces'].append(space_rect)
                space_index = len(page['spaces']) - 1

            # Extract each <TextBlock>:
            for block_el in space_el[0]:
                block = {
                    'id': block_el.attrib['ID'],
                    'rect': rect(block_el.attrib),
                    'class': labels_by_tagref[block_el.attrib['TAGREFS']],
                }

                # annotate blocks that have an atypical PrintSpace (if there are any)
                if space_index is not None:
                    block['space'] = space_index

                # check for redacted blocks
                if redacted_storage and block['id'] not in unredacted_block_ids:
                    block['redacted'] = True

                # handle <Illustration>
                if block_el.tag == 'Illustration':
                    block['format'] = 'image'

                    # read image data
                    with unredacted_storage.open('images/%s' % page['file_name']) as in_file:
                        with tempfile.NamedTemporaryFile(suffix='.tif') as temp_img:
                            temp_img.write(in_file.read())
                            temp_img.flush()
                            img = Image.open(temp_img.name)
                            img.load()
                    r = block['rect']
                    cropped_img = img.crop((r[0], r[1], r[0]+r[2], r[1]+r[3]))

                    # store image data as data url on block
                    png_data = BytesIO()
                    cropped_img.save(png_data, 'PNG')
                    block['data'] = 'image/png;base64,' + b64encode(png_data.getvalue()).decode('utf8')

                # handle <TextBlock>
                else:
                    tokens = block['tokens'] = []
                    last_font = None
                    redacted_span = False
                    check_string_redaction = redacted_storage and not block.get('redacted', False)

                    # handle <TextLine>
                    for line_el in block_el.iter('TextLine'):
                        tokens.append(['line', {'rect': rect(line_el.attrib)}])

                        # handle <String>
                        for string in line_el.iter('String'):
                            string_attrib = string.attrib  # for speed

                            # Handle STYLEREFS attribute: start and stop a ['font', {'id':CaseFont.id}] span each
                            # time the style changes.
                            font = string_attrib['STYLEREFS']
                            if font != last_font:
                                if last_font:
                                    tokens.append(['/font'])
                                tokens.append(['font', {'id': fonts_by_style_id[font]}])
                                last_font = font

                            # Handle redaction: start and stop a ['redact'] span each time we enter or leave a redacted
                            # region.
                            if check_string_redaction:
                                if redacted_span:
                                    if string_attrib['ID'] in unredacted_string_ids:
                                        tokens.append(['/redact'])
                                        redacted_span = False
                                else:
                                    if string_attrib['ID'] not in unredacted_string_ids:
                                        tokens.append(['redact'])
                                        redacted_span = True

                            # Write an ['ocr', {'rect':<bounding box>, 'wc':<word confidence>, 'cc':<character confidence>}]
                            # span for each word.
                            ocr_token = ['ocr', {'rect': rect(string_attrib), 'wc': float(string_attrib['WC'])}]

                            # cc is a string of zeroes for each high-confidence character and nines for each low-confidence
                            # character. We don't store all-zero strings at all. For strings with some nines, convert to
                            # binary and interpret as an integer for compactness.
                            cc = string_attrib['CC']
                            if '9' in cc:
                                ocr_token[1]['cc'] = int(cc.replace('9', '1'), 2)

                            # Handle CONTENT attribute: append a space if next tag is a space, or if string does not
                            # end with a hyphen.
                            text = string_attrib['CONTENT']
                            next_tag = string.getnext()
                            if (next_tag is not None and next_tag.tag == 'SP') or (text and text[-1] not in ('-', '\xad')):
                                text += ' '

                            # <String CONTENT> can be empty, so only include text if it's filled in:
                            if text:
                                tokens.extend((ocr_token, text, ['/ocr']))
                            else:
                                tokens.extend((ocr_token, ['/ocr']))

                        tokens.append(['/line'])

                    # close open spans
                    if last_font:
                        tokens.append(['/font'])
                    if redacted_span:
                        tokens.append(['/redact'])

                page['blocks'].append(block)
        pages.append(page)

    ### Extract data for each case into the cases dict ###

    print("Reading Case files")
    blocks_by_id = {block['id']: block for page in pages for block in page['blocks']}
    for path in paths['case']:
        print(path)

        parsed = parse(unredacted_storage, path, remove_namespaces=False)
        duplicative = bool(parsed('duplicative|casebody'))

        if not duplicative:
            # reorder head matter, and confirm that all elements are preserved
            # (we have to do this during ingest so footnotes are linked up properly)
            casebody = parsed('casebody|casebody')
            ids_before_reorder = {el.attr.id for el in casebody('[id]').items()}
            CaseXML.reorder_head_matter(parsed)
            ids_after_reorder = {el.attr.id for el in casebody('[id]').items()}
            if ids_before_reorder != ids_after_reorder:
                raise Exception("reorder_head_matter id mismatch for %s" % path)

        parsed = parsed.remove_namespaces()
        casebody = parsed('casebody')
        case = {'path': str(path)}
        metadata = case['metadata'] = {
            'first_page': casebody.attr.firstpage,
            'last_page': casebody.attr.lastpage,
        }

        if duplicative:
            # extract metadata for duplicative case
            case_number = parsed('fileGrp[USE="casebody"] > file').attr.ID.split('_')[1]
            case['id'] = '%s_%s' % (volume_barcode, case_number)
            metadata['duplicative'] = True

        else:
            # extract metadata for non-duplicative case (<case> element)
            case_el = parsed('case')
            case['id'] = case_el.attr.caseid
            metadata['duplicative'] = False
            metadata['status'] = case_el.attr.publicationstatus
            metadata['decision_date'] = case_el('decisiondate').text()
            court = case_el('court')
            metadata['court'] = {
                'abbreviation': court.attr.abbreviation,
                'jurisdiction': court.attr.jurisdiction,
                'name': court.text(),
            }
            district = case_el('district')
            if district.length:
                metadata['district'] = {
                    'name': district.text(),
                    'abbreviation': district.attr.abbreviation,
                }
            argument_date = case_el('argumentdate')
            if argument_date.length:
                metadata['argument_date'] = argument_date.text()
            name = case_el('name')
            metadata['name'] = name.text()
            metadata['name_abbreviation'] = name.attr.abbreviation
            metadata['docket_numbers'] = [el.text() for el in case_el('docketnumber').items() if el.text()]
            metadata['citations'] = [{
                'category': cite.attr.category,
                'type': cite.attr.type,
                'text': cite.text(),
            } for cite in case_el('citation').items()]

        # build lookup table of case paragraph ID -> [ALTO block IDs]
        case_id_to_alto_ids = {}
        for xref_el in parsed('div[TYPE="blocks"] > div[TYPE="element"]').items():
            par_el, blocks_el = xref_el('fptr').items()
            case_id_to_alto_ids[par_el('area').attr.BEGIN] = [block_el.attr.BEGIN for block_el in blocks_el('area').items()]

        # extract each <opinion> from the <casebody> for processing
        if duplicative:
            # for duplicative cases, create fake <opinion> with direct children of <casebody>, with type 'unprocessed'
            sections = [['unprocessed', casebody.children().items()]]
        else:
            # for non-duplicative case, create fake <opinion> with elements appearing before first opinion, type 'head'
            head_matter_children = casebody.children(':not(opinion):not(corrections)').items()
            opinion_els = [[el.attr.type, list(el.children().items())] for el in casebody.children('opinion').items()]
            sections = [['head', list(head_matter_children)]] + opinion_els

            # add 'ref' attribute to each <bracketnum>, linking to ID of each <headnotes> element if possible
            headnotes_lookup = {}
            for headnote in casebody('headnotes').items():
                number = re.match(r'\d+', headnote.text())
                if number:
                    headnotes_lookup[number.group(0)] = headnote.attr.id
            for headnote_ref in casebody('bracketnum').items():
                number = re.search(r'\d', headnote_ref.text())
                if number and number.group(0) in headnotes_lookup:
                    headnote_ref.attr.ref = headnotes_lookup[number.group(0)]

        # handle each <opinion>
        case['opinions'] = opinions = []
        for footnote_opinion_index, (op_type, children) in enumerate(sections):

            # link footnotes:
            # add id='footnote_<opinion count>_<footnote count>' attribute to each <footnote>
            # add ref='<footnote_id>' attribute to each <footnotemark>
            if not duplicative:
                footnote_index = 1
                footnotes_lookup = {}
                for tag in children:
                    if tag[0].tag == 'footnote':
                        footnote_id = 'footnote_%s_%s' % (footnote_opinion_index, footnote_index)
                        tag.attr.id = footnote_id
                        if tag.attr.label:
                            footnotes_lookup[tag.attr.label] = footnote_id
                        footnote_index += 1
                for tag in children:
                    for footnote_ref in tag.find('footnotemark').items():
                        if footnote_ref.text() in footnotes_lookup:
                            footnote_ref.attr.ref = footnotes_lookup[footnote_ref.text()]

            # extract data for this opinion, and update alto data to match
            opinion = {'type': op_type}
            paragraphs, footnotes, paragraph_els = extract_paragraphs(children, case_id_to_alto_ids, blocks_by_id)
            sync_alto_blocks_with_case_paragraphs(paragraph_els, blocks_by_id, case_id_to_alto_ids)
            if paragraphs:
                opinion['paragraphs'] = paragraphs
            if footnotes:
                opinion['footnotes'] = footnotes
            opinions.append(opinion)

        # handle <corrections>
        if not duplicative:
            corrections = list(case_el.children('correction').items())
            if corrections:
                case['corrections'] = [el.text() for el in corrections]

        cases.append(case)

    # encrypt redacted strings
    if redacted_storage:
        print("Encrypting pages")
        for page in pages:
            page_obj = PageStructure(blocks=page['blocks'])
            page_obj.encrypt(key)
            page['encrypted_strings'] = page_obj.encrypted_strings

        # create an unencrypted copy for checking reversability
        print("Decrypting pages")
        decrypted_pages = deepcopy(pages)
        for page in decrypted_pages:
            page_obj = PageStructure(blocks=page['blocks'], encrypted_strings=page['encrypted_strings'])
            page_obj.decrypt(key)
        blocks_by_id = {block['id']: block for page in decrypted_pages for block in page['blocks']}
    else:
        decrypted_pages = pages

    ### validate results

    # Here we build fake Django objects and make sure we can render the extracted data back into XML that matches
    # the source files.

    renderer = render_case.VolumeRenderer(blocks_by_id, fonts_by_id, {})  # we don't need labels_by_block_id because original_xml cases don't include page numbers

    # validate volume dict
    volume_obj = VolumeMetadata(barcode=volume_barcode, xml_metadata=volume['metadata'])
    new_xml = renderer.render_volume(volume_obj)
    parsed = parse(unredacted_storage, paths['volume'][0])
    volume_el = parsed('volume')
    old_xml = str(volume_el)
    old_xml = old_xml.replace('<nominativereporter abbreviation="" volnumber=""/>', '')  # remove blank <normativereporter>
    xml_strings_equal(new_xml, old_xml)

    # validate pages dict
    print("Checking ALTO integrity")
    for page in decrypted_pages:
        page_obj = create_page_obj(volume_obj, page)
        to_test = [(unredacted_storage, page['path'], False)]
        if redacted_storage:
            to_test.append((redacted_storage, page['path'].replace('unredacted', 'redacted'), True))
        for storage, path, redacted in to_test:
            print("- checking %s" % path)
            parsed = parse(storage, path)
            alto_xml_output = renderer.render_page(page_obj, redacted)
            original_alto = str(parsed('Page'))
            original_alto = original_alto.replace('WC="1.0"', 'WC="1.00"')  # normalize irregular decimal places
            original_alto = original_alto.replace('CC=""', 'CC="0"')  # normalize character confidence for empty strings -- some are CC="", some are CC="0"

            # validate everything *except* the attributes listed here, which are permanently stripped:
            xml_strings_equal(alto_xml_output, original_alto, {
                'tag_attrs': {
                    'Page': {'ID', 'PHYSICAL_IMG_NR', 'xmlns'},
                    'PrintSpace': {'ID'},
                    'TextBlock': {'TAGREFS'},
                    'Illustration': {'TAGREFS'},
                    'TextLine': {'ID'},
                    'String': {'ID', 'TAGREFS'},
                    'SP': {'HPOS', 'ID', 'VPOS', 'WIDTH'}
                }
            })

    # validate cases
    print("Checking case integrity")
    for case in cases:
        # create fake CaseMetadata object
        case_obj = CaseMetadata(case_id=case['id'], volume=volume_obj, duplicative=case['metadata']['duplicative'],
                                first_page=case['metadata']['first_page'], last_page=case['metadata']['last_page'])
        case_obj.structure = CaseStructure(metadata=case_obj, opinions=case['opinions'], corrections=case.get('corrections') or None)
        case_obj.initial_metadata = CaseInitialMetadata(case=case_obj, metadata=case['metadata'])

        to_test = [(unredacted_storage, case['path'], False)]
        if redacted_storage:
            to_test.append((redacted_storage, case['path'].replace('unredacted', 'redacted'), True))

        for storage, path, redacted in to_test:
            # load comparison xml
            print("- checking %s" % path)
            parsed = parse(storage, path, remove_namespaces=False)
            CaseXML.reorder_head_matter(parsed)
            parsed = parsed.remove_namespaces()

            # compare <casebody>
            renderer.redacted = redacted
            new_casebody = renderer.render_orig_xml(case_obj)
            old_casebody = str(parsed('casebody'))

            # remove whitespace from start and end of these tags:
            strip_whitespace_els = 'blockquote|author|p|headnotes|history|disposition|syllabus|summary|attorneys|judges|otherdate|decisiondate|parties|seealso|citation|docketnumber|court'
            old_casebody = re.sub(r'(<(?:%s)[^>]*>)\s+' % strip_whitespace_els, r'\1', old_casebody, flags=re.S)
            old_casebody = re.sub(r'\s+(</(?:%s)>)' % strip_whitespace_els, r'\1', old_casebody, flags=re.S)
            old_casebody = old_casebody.replace(' label=""', '')  # footnote with empty label

            # normalize multiple spaces
            old_casebody = re.sub(r' +', ' ', old_casebody)
            new_casebody = re.sub(r' +', ' ', new_casebody)

            xml_strings_equal(new_casebody, old_casebody, {
                'attrs': {'pgmap', 'xmlns'},
                'tag_attrs': {
                    'footnote': {'redact'},  # the redact attr isn't reliably set in the original, so our output may not match. comparison will still ensure that redacted footnotes don't appear.
                }
            })

            # compare <case>
            if not case_obj.duplicative:
                new_case_head = renderer.render_case_header(case_obj.case_id, case_obj.initial_metadata.metadata)
                old_case_head = str(parsed('case'))
                old_case_head = old_case_head.replace('<docketnumber/>', '')
                xml_strings_equal(new_case_head, old_case_head)

    ### validate results

    # write the results out to a zip file

    out_path = Path('token_streams', unredacted_storage.path.name+'.zip')
    print("Writing temp files to %s" % out_path)
    font_attrs = ['family', 'size', 'style', 'type', 'width']
    fonts_by_id = {f.id: {attr: getattr(f, attr) for attr in font_attrs} for f in fonts_by_id.values()}
    if captar_storage.exists(str(out_path)):
        captar_storage.delete(str(out_path))
    with tempfile.SpooledTemporaryFile(max_size=2**20*100) as tmp:
        with ZipFile(tmp, 'w') as zip:
            for path, obj in (('volume.json', volume), ('pages.json', pages), ('cases.json', cases), ('fonts.json', fonts_by_id)):
                zip.writestr(path, json.dumps(obj))
        tmp.seek(0)
        captar_storage.save(str(out_path), tmp)

### write to database

@shared_task
def write_to_db(volume_barcode, zip_path):
    """
        Given a zip file created by volume_to_json, ingest captar data.
    """
    # load data from zip
    print("Loading data for volume %s from %s" % (volume_barcode, zip_path))
    with captar_storage.open(zip_path, 'rb') as raw:
        with ZipFile(raw) as zip:
            volume = json.loads(zip.open('volume.json').read().decode('utf8'))
            pages = json.loads(zip.open('pages.json').read().decode('utf8'))
            cases = json.loads(zip.open('cases.json').read().decode('utf8'))
            fonts_by_fake_id = json.loads(zip.open('fonts.json').read().decode('utf8'))

    # save CaseFonts
    # do this outside the transaction so volumes can see the same fonts while importing in parallel
    print("Saving fonts")
    font_fake_id_to_real_id = {}
    fonts_by_id = {}
    for font_fake_id, font_attrs in fonts_by_fake_id.items():
        font_obj, _ = CaseFont.objects.get_or_create(**font_attrs)
        font_fake_id_to_real_id[int(font_fake_id)] = font_obj.pk
        fonts_by_id[font_obj.pk] = font_obj

    with transaction.atomic(using='capdb'):

        # save volume
        try:
            volume_obj = VolumeMetadata.objects.get(barcode=volume_barcode)
        except VolumeMetadata.DoesNotExist:
            # fake up a volume for testing
            volume_obj = VolumeMetadata(barcode=volume_barcode)
            volume_obj.reporter, _ = Reporter.objects.get_or_create(short_name=volume['metadata']['reporter']['abbreviation'], defaults={'full_name': volume['metadata']['reporter']['name'], 'updated_at': timezone.now(), 'created_at': timezone.now(), 'hollis':[]})
        volume_obj.xml_metadata = volume['metadata']
        volume_obj.save()

        # save TarFile
        ingest_source, _ = TarFile.objects.get_or_create(storage_path=volume['metadata']['tar_path'], hash=volume['metadata']['tar_hash'], volume=volume_obj)


        # In volume_to_json we generated fake CaseFont IDs that were inserted into the pages dict. Replace those with
        # the real ones:
        for page in pages:
            page['font_names'] = {font_fake_id_to_real_id[int(k)]:v for k,v in page['font_names'].items()}
            for block in page['blocks']:
                for token in block.get('tokens', []):
                    if type(token) != str and token[0] == 'font':
                        token[1]['id'] = font_fake_id_to_real_id[token[1]['id']]

        # clear existing imports
        # TODO: testing only?
        print("Deleting existing items")
        CaseStructure.objects.filter(metadata__volume=volume_obj).delete()
        CaseInitialMetadata.objects.filter(case__volume=volume_obj).delete()
        volume_obj.page_structures.all().delete()

        # save pages
        print("Saving pages")
        page_objs = PageStructure.objects.bulk_create(create_page_obj(volume_obj, page, ingest_source) for page in pages)

        # save cases
        print("Saving cases")
        case_objs = []
        initial_metadata_objs = []
        for case in cases:
            try:
                metadata_obj = CaseMetadata.objects.get(case_id=case['id'])
            except CaseMetadata.DoesNotExist:
                metadata_obj = CaseMetadata(case_id=case['id'], reporter=volume_obj.reporter, volume=volume_obj)
                metadata_obj.save()
            case_objs.append(CaseStructure(metadata=metadata_obj, opinions=case['opinions'], corrections=case.get('corrections') or None, ingest_source=ingest_source, ingest_path=case['path']))
            initial_metadata_objs.append(CaseInitialMetadata(case=metadata_obj, metadata=case['metadata'], ingest_source=ingest_source, ingest_path=case['path']))
        case_objs = CaseStructure.objects.bulk_create(case_objs)
        initial_metadata_objs = CaseInitialMetadata.objects.bulk_create(initial_metadata_objs)

        # save join table between CaseStructure and PageStructure
        print("Saving join table")
        page_objs_by_block_id = {block['id']:p for p in page_objs for block in p.blocks}
        links = {(case.id, page_objs_by_block_id[block_id].id)
                 for case in case_objs
                 for par in iter_pars(case.opinions)
                 for block_id in par['block_ids']}
        link_objs = [CaseStructure.pages.through(casestructure_id=case_id, pagestructure_id=page_id) for case_id, page_id in links]
        CaseStructure.pages.through.objects.bulk_create(link_objs)

        # update CaseBodyCache and CaseMetadata based on newly loaded data
        print("Caching data")
        blocks_by_id = PageStructure.blocks_by_id(page_objs)
        for case in case_objs:
            case.metadata.sync_from_initial_metadata(force=True)
            case.metadata.sync_case_body_cache(blocks_by_id=blocks_by_id, fonts_by_id=fonts_by_id)
