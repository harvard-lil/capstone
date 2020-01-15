import bisect
import difflib
import json
import re
import shutil
import subprocess
import tempfile
from base64 import b64encode
from collections import defaultdict
from io import BytesIO
from zipfile import ZipFile, ZIP_BZIP2
from pathlib import Path
from PIL import Image
from pyquery import PyQuery
from celery import shared_task
from diff_match_patch import diff_match_patch
from lxml import etree

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from capdb.models import CaseFont, PageStructure, VolumeMetadata, CaseMetadata, CaseStructure, Reporter, \
    CaseInitialMetadata, CaseXML, TarFile
from capdb.storages import captar_storage, CapS3Storage, CaptarStorage
from scripts import render_case
from scripts.compress_volumes import files_by_type, open_captar_volume
from scripts.helpers import parse_xml, fix_image_file_name
from scripts.render_case import iter_pars


### HELPERS ###

def scan_dupe_paragraphs():
    """
        Check captar files for paragraphs where the second half is a repeat of the first half. Some of these are caused
        by a processing bug that replaces one ALTO paragraph with another. Others are benign, such as when a case
        repeats the party names twice.
    """
    dupes = []
    for zip_path in captar_storage.iter_files('unredacted'):
        print("Scanning %s" % zip_path)
        with open_captar_volume(Path(zip_path), False) as unredacted_storage:
            paths = files_by_type(sorted(unredacted_storage.iter_files_recursive()))
            for path in paths['case']:
                parsed = parse(unredacted_storage, path)
                for par in parsed("casebody [id]").items():
                    text = par.text()
                    if len(text) < 20:
                        continue
                    text = text.replace('\xad', '').replace('-', '')
                    if text[-(len(text) // 2):] == text[:len(text) // 2]:
                        print(path, par)
                        dupes.append([path, str(par)])
    Path('test_data/zips/duplicate_pars.json').write_text(json.dumps(dupes, indent=4))

def dump_image(storage, image_name):
    """ Export an image for debugging, e.g. 32044066192519_00115_0.tif """
    in_path = Path('images', image_name)
    out_path = Path('test_data/zips/dump', in_path)
    out_path.parent.mkdir(exist_ok=True, parents=True)
    print("Dumping %s" % out_path)
    out_path.write_bytes(storage.contents(in_path, 'rb'))


def dump_text(path, text):
    path = Path('test_data/zips/dump', path)
    print("Dumping %s" % path)
    path.write_text(text)

def dump_files_for_case(volume_barcode, old_casebody, new_casebody, redacted, unredacted_storage, redacted_storage, case, pages, renderer, blocks_by_id):
    """
        For debugging when a case fails to match during assert_reversability -- dump case and alto files locally:
            unredacted_storage.parent.location = redacted_storage.parent.location = 'test_data/zips'
            dump_files_for_case(volume_barcode, old_casebody, new_casebody, redacted, unredacted_storage, redacted_storage, case, pages, renderer, blocks_by_id)
    """
    page_objs_by_block_id = {block['id']: p for p in pages for block in p['blocks']}
    case_pages = {}
    for par in iter_pars(case['opinions']):
        for block_id in par['block_ids']:
            page = page_objs_by_block_id[block_id]
            case_pages[page['id']] = page
    case_pages = sorted(case_pages.values(), key=lambda page: page['path'])
    to_dump = (
            [(unredacted_storage, case['path'])] +
            [(unredacted_storage, page['path']) for page in case_pages]
    )
    if redacted_storage:
        to_dump += [(redacted_storage, path.replace('unredacted', 'redacted')) for _, path in to_dump]
    for storage, path in to_dump:
        path = path[:-3]
        out_path = Path(path)
        out_path.parent.mkdir(exist_ok=True, parents=True)
        dump_text(out_path, storage.contents(path))
    for page in case_pages:
        dump_image(unredacted_storage, page['file_name'])
    dump_text("%s-old-case-%s.xml" % (volume_barcode, 'redacted' if redacted else 'unredacted'), old_casebody)
    dump_text("%s-new-case-%s.xml" % (volume_barcode, 'redacted' if redacted else 'unredacted'), new_casebody)
    dump_text("%s-case-structure.json" % volume_barcode, json.dumps(renderer.hydrate_opinions(case['opinions'], blocks_by_id), indent=2))

def dump_files_for_page(volume_barcode, redacted, alto_xml_output, original_alto, page, unredacted_storage, redacted_storage):
    """
        For debugging when an alto file fails to match during assert_reversability.
    """
    path = page['path'][:-3]
    dump_text(path, unredacted_storage.contents(path))
    if redacted_storage:
        path = path.replace('unredacted', 'redacted')
        dump_text(path, redacted_storage.contents(path))
    dump_text("%s-old-alto-%s.xml" % (volume_barcode, 'redacted' if redacted else 'unredacted'), original_alto)
    dump_text("%s-new-alto-%s.xml" % (volume_barcode, 'redacted' if redacted else 'unredacted'), alto_xml_output)
    dump_text("%s-alto-structure.json" % volume_barcode, json.dumps(page, indent=2))

# Some different ways to exclude files from validation, or patch their contents:
skip_redacted_validation = {
    # Footnote marks on the <docketnumber> were not properly redacted in these Kansas volumes
    # Example of individual fixes, which I gave up on:
    # "alto/32044073040222_redacted_ALTO_00146_1.xml.gz": [('[ID="SP_292.6.1.4"],[ID="ST_292.6.1.5"]', 'delete')],
    # "alto/32044073040222_redacted_ALTO_00256_0.xml.gz": [('[ID="SP_511.6.1.4"],[ID="ST_511.6.1.5"]', 'delete')],
    # "alto/32044073040222_redacted_ALTO_00377_0.xml.gz": [('[ID="SP_753.6.1.4"],[ID="ST_753.6.1.5"]', 'delete')],
    '32044073040222','32044078453420','32044132275520','32044142600170',
}
skip_validation_files = {}
special_text_replacements = {
    # footnotemark inconsistently added to unredacted casemets because ’ identified as 1
    "casemets/32044066192519_unredacted_CASEMETS_0019.xml.gz": [('<footnotemark>1</footnotemark>', '’')],
    "casemets/32044066192519_redacted_CASEMETS_0019.xml.gz": [('Emporia, Kansas. At the instant', 'Emporia, Kansas.’ At the instant')],
    # extra hyphen in redacted case but not redacted alto
    "casemets/32044078515160_redacted_CASEMETS_0036.xml.gz": [('­There was evidence', 'There was evidence')],
    "casemets/32044078515160_redacted_CASEMETS_0184.xml.gz": [('­-In accordance with the authority', '-In accordance with the authority')],
    "casemets/32044078639846_redacted_CASEMETS_0260.xml.gz": [('­VI. On the subject', 'VI. On the subject')],
    "casemets/32044078639762_redacted_CASEMETS_0057.xml.gz": [('­IV. Defendant contends that the', 'IV. Defendant contends that the')],
    "casemets/32044078493681_redacted_CASEMETS_0030.xml.gz": [('­But even so, the appellee', 'But even so, the appellee')],
    "casemets/32044078639804_redacted_CASEMETS_0002.xml.gz": [('­Defendant moved to strike', 'Defendant moved to strike')],
    "casemets/32044078499704_redacted_CASEMETS_0070.xml.gz": [('­• We find this proceeding', '• We find this proceeding')],
    "casemets/32044078566742_redacted_CASEMETS_0016.xml.gz": [('­In its motion for a rehearing', 'In its motion for a rehearing')],
    "casemets/32044078680782_redacted_CASEMETS_0042.xml.gz": [('­-In view of deficiencies of', '-In view of deficiencies of')],
    "casemets/32044078639879_redacted_CASEMETS_0002.xml.gz": [('­Hence this case should be', 'Hence this case should be')],
    "casemets/32044078565546_redacted_CASEMETS_0040.xml.gz": [('­The evidence is undisputed', 'The evidence is undisputed')],
    "casemets/32044078639838_redacted_CASEMETS_0128.xml.gz": [('­II. The second point made', 'II. The second point made')],
    "casemets/32044078499399_redacted_CASEMETS_0023.xml.gz": [('­-As the rule now stands', '-As the rule now stands')],
    "casemets/32044078498003_redacted_CASEMETS_0056.xml.gz": [('­-The amount of evidence required', '-The amount of evidence required')],
    "casemets/32044078515210_redacted_CASEMETS_0103.xml.gz": [('­-It will be observed that', '-It will be observed that')],
    # case is missing an alto block reference
    "casemets/32044133498154_unredacted_CASEMETS_0058.xml.gz": [(
        '<area BEGIN="BL_456.1" BETYPE="IDREF" FILEID="alto_00228_1"/>',
        '<area BEGIN="BL_455.17" BETYPE="IDREF" FILEID="alto_00228_0"/><area BEGIN="BL_456.1" BETYPE="IDREF" FILEID="alto_00228_1"/>',
    )],
}
special_cases = {
    # footnotemark inconsistently added to unredacted casemets because ’ identified as 1
    "alto/32044066192519_unredacted_ALTO_00115_0.xml.gz": [('[ID="ST_229.1.3.3"]', 'attrs', {"CONTENT": "Kansas.’", "CC": "00000000"})],
    "alto/32044066192519_redacted_ALTO_00115_0.xml.gz": [('[ID="ST_229.1.3.3"]', 'attrs', {"CONTENT": "Kansas.’", "CC": "00000000"})],
    # footnotemark should have been redacted from ALTO, as it is in casemets
    # (could possibly detect automatically by checking redacted="true" value on related footnote)
    "alto/32044078581188_redacted_ALTO_00159_0.xml.gz": [('[ID="ST_317.4.16.3"],[ID="SP_317.4.16.4"]', 'delete')],
    "alto/32044078581204_redacted_ALTO_00112_1.xml.gz": [('[ID="ST_224.1.13.7"],[ID="SP_224.1.13.8"]', 'delete')],
}

def apply_special_cases(path, parsed):
    """
        If path appears in special_cases, replace attribute and text values for given selectors.
    """
    if path in special_cases:
        for selector, op, *args in special_cases[path]:
            el = parsed(selector)
            if op == 'text':
                el.text(args[0])
            elif op == 'replace_text':
                el.text(el.text().replace(*args))
            elif op == 'delete':
                el.remove()
            elif op == 'attrs':
                el[0].attrib.update(args[0])
    return parsed

def apply_text_replacements(path, text, text_replacements):
    """
        If path appears in text_replacements, replace each old value with new value in order.
    """
    if path in text_replacements:
        for old_val, new_val in text_replacements[path]:
            text = text.replace(old_val, new_val)
    return text

def rect(el_attrib):
    """ Convert an XML element like <foo HPOS="1" VPOS="2" WIDTH="3" HEIGHT="4"> to [1, 2, 3, 4]. """
    return (
        float(el_attrib['HPOS']) if '.' in el_attrib['HPOS'] else int(el_attrib['HPOS']),
        float(el_attrib['VPOS']) if '.' in el_attrib['VPOS'] else int(el_attrib['VPOS']),
        float(el_attrib['WIDTH']) if '.' in el_attrib['WIDTH'] else int(el_attrib['WIDTH']),
        float(el_attrib['HEIGHT']) if '.' in el_attrib['HEIGHT'] else int(el_attrib['HEIGHT']),
    )

def parse(storage, path, remove_namespaces=True, text_replacements=None):
    """ Extract .gz-compressed XML path from storage, and return as PyQuery object. """
    text = storage.contents(path[:-3])  # strip .gz so captar_storage will decompress for us
    text = apply_text_replacements(path, text, special_text_replacements)
    if text_replacements:
        text = apply_text_replacements(path, text, text_replacements)
    xml = parse_xml(text)
    apply_special_cases(path, xml)
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
            >>> assert diff_strings(blocks_text, case_text) == [
            ...     ('equal', 0, 4, 0, 4),
            ...     ('replace', 4, 5, 4, 5),
            ...     ('equal', 5, 9, 5, 9),
            ...     ('replace', 9, 10, 9, 10),
            ...     ('equal', 10, 14, 10, 14),
            ...     ('delete', 14, 15, 14, 14),
            ...     ('equal', 15, 19, 14, 18),
            ...     ('insert', 19, 19, 18, 19)]
            >>> assert diff_strings(blocks_text, case_text) == difflib.SequenceMatcher(None, blocks_text, case_text).get_opcodes()
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
        >>> assert list(tokenize_element(etree.XML("<p>text <footnotemark ref='foo'>1</footnotemark> text</p>"))) == [
        ...     'text ', ['footnotemark', {'ref':'foo'}], '1', ['/footnotemark'], ' text']
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
        >>> assert insert_tags(block, 1, 2, [['new'], ['stuff']]) == 3
        >>> assert block == ['foo', 'ba', ['new'], ['stuff'], 'r']
    """
    text = block[i]
    to_insert = [token for token in [text[:offset]]+new_tokens+[text[offset:]] if token]
    block[i:i + 1] = to_insert
    return len(to_insert) - 1

# use this special constant (a unicode reserved codepoint) to indicate where <footnotemark> and <bracketnum> tags
# appear in the ALTO and case files, to help with lining up diffs.
tag_marker = '\uE000'
tag_name_lookup = {
    tag_marker: 'bracketnum',
    chr(ord(tag_marker)+1): '/bracketnum',
    chr(ord(tag_marker)+2): 'footnotemark',
    chr(ord(tag_marker)+3): '/footnotemark',
}
tag_marker_lookup = {v:k for k,v in tag_name_lookup.items()}
tag_marker_re = re.compile(r'([%s])' % "".join(tag_name_lookup.keys()))

def index_blocks(blocks):
    """
        Given a list of blocks, return:
            (a) the combined text from the blocks
            (b) the offsets mapping from that text back to each string in the blocks
            (c) a lookup of the strings themselves
            (d) a list of all tag marker names in the text

        Example:
        >>> blocks = [[tag_marker_lookup['bracketnum']+'foo'+tag_marker_lookup['/bracketnum'], ['tag'], 'bar'], ['baz']]
        >>> blocks_text, blocks_offsets, blocks_lookup, block_tag_names = index_blocks(blocks)
        >>> assert blocks_text == '%sfoo%sbarbaz' % (tag_marker, tag_marker)
        >>> assert blocks_offsets == [0, 5, 8]
        >>> assert blocks_lookup == [
        ...     (0, ['%sfoo%s' % (tag_marker, tag_marker), ['tag'], 'bar'], 0),
        ...     (5, ['%sfoo%s' % (tag_marker, tag_marker), ['tag'], 'bar'], 2),
        ...     (8, ['baz'], 0)]
        >>> assert block_tag_names == ['bracketnum', '/bracketnum']

        This allows us to start from the combined text and use it to modify the individual strings in the blocks object.
        For example, if we want to modify blocks_text[5] (an 'r'), we can search blocks_offsets to figure out that it is part
        of entry 1 (because it is after 3 and before 6), and then use blocks_lookup[1] to update the original string.
    """
    blocks_text = ''
    blocks_offsets = []
    blocks_lookup = []
    block_tag_names = []
    for block in blocks:
        for i, token in enumerate(block):
            if type(token) == str:

                # replace individual tag markers with base tag_marker
                tag_markers = tag_marker_re.findall(token)
                if tag_markers:
                    token = tag_marker_re.sub(tag_marker, token)
                    block[i] = token
                    block_tag_names.extend(tag_name_lookup[i] for i in tag_markers)

                blocks_offsets.append(len(blocks_text))
                blocks_lookup.append((len(blocks_text), block, i))
                blocks_text += token
    return blocks_text, blocks_offsets, blocks_lookup, block_tag_names

def sync_alto_blocks_with_case_tokens(alto_blocks, case_tokens):
    """
        Given a list of blocks of tokens from ALTO, and a single tokenized paragraph from CaseMETS, add 'edit' tags to
        make the ALTO text match the case text. Then import all tags from the CaseMETS (such as footnotemark) into the
        ALTO. Example:
        >>> alto_blocks = [[["baz"], "abc-", "def"], ["gh-i", "jkl", ["/baz"]]]
        >>> case_tokens = [["bar"], "abcd", ["foo"], "efg", ['/foo'], "hijkl", ["/bar"]]
        >>> sync_alto_blocks_with_case_tokens(alto_blocks, case_tokens)
        >>> assert alto_blocks == [[['baz'], ['edit', {'was': ''}], ['bar'], ['/edit'], 'abc', ['edit', {'was': '-'}], ['/edit'], 'd', ['edit', {'was': ''}], ['foo'], ['/edit'], 'ef'], ['g', ['edit', {'was': ''}], ['/foo'], ['/edit'], 'h', ['edit', {'was': '-'}], ['/edit'], 'i', 'jkl', ['edit', {'was': ''}], ['/bar'], ['/edit'], ['/baz']]]
    """

    ## initial indexing ##

    # Break out the new tokens into a list of non-text tokens in [offset, token] form, and a string of the text tokens
    case_tags = []
    case_text = []
    for token in case_tokens:
        if type(token) == str:
            case_text.append(token)
        else:
            case_tags.append(token)
            case_text.append(tag_marker)
    case_text = "".join(case_text).strip()  # remove any whitespace at start and end of paragraph of case text

    blocks_text, blocks_offsets, blocks_lookup, block_tag_names = index_blocks(alto_blocks)

    ## text update -- update ALTO text to match case text ##

    if case_text != blocks_text:

        ## get diff
        if case_tags and block_tag_names == [tag[0] for tag in case_tags]:
            # if there are matching footnote/bracket marks in the text, split around those and diff each range
            # separately, so edits stay on the right side of the tags
            b_parts = blocks_text.split(tag_marker)
            c_parts = case_text.split(tag_marker)
            diff = []
            b_offset = c_offset = 0
            for b, c in zip(b_parts, c_parts):
                for tag, i1, i2, j1, j2 in diff_strings(b, c):
                    diff.append([tag, i1+b_offset, i2+b_offset, j1+c_offset, j2+c_offset])
                b_offset += len(b)+1
                c_offset += len(c)+1
        else:
            # otherwise diff entire string
            diff = diff_strings(blocks_text, case_text)

        # Get all differences between alto text and case text,
        # in order from end to start so we don't mess up indexes as we make edits.
        # tag will be "insert", "replace", or "delete"
        # i1:i2 will be the target range in the alto text, and j1:j2 will be the source range in the case text
        for tag, i1, i2, j1, j2 in reversed(diff):
            if tag == 'equal':
                continue

            # find the target block for this edit
            block_index = bisect.bisect_right(blocks_offsets, i1) - 1
            offset, block, i = blocks_lookup[block_index]

            # Check if we should use block to left instead:
            # When we're inserting to the left edge of the string, it's equally valid to insert on right edge of previous
            # string. We'd rather do that unless the previous string ends in a space.
            if i1 == offset and block_index > 0:
                left_offset, left_block, left_i = blocks_lookup[block_index - 1]
                if left_block[left_i][-1] != ' ':
                    offset, block, i = left_offset, left_block, left_i
                    block_index -= 1

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
                ['edit', {'was': removed.replace(tag_marker, '')}],
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
                    ['edit', {'was': removed.replace(tag_marker, '')}],
                    ['/edit'],
                ])
                len_to_remove -= len(removed)

    # replace tag markers with tags from case_tags list
    for block in reversed(alto_blocks):
        for i in range(len(block)-1, -1, -1):
            token = block[i]
            if type(token) == str:
                if tag_marker in token:
                    parts = token.split(tag_marker)
                    tags = case_tags[-len(parts)+1:]
                    del case_tags[-len(tags):]
                    new_tokens = ([parts[0]] if parts[0] else []) + [i for a in zip(tags, parts[1:]) for i in a if i]
                    block[i:i+1] = new_tokens

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

        # Special case for insertion on left edge of redaction:
        # If we're inserting text on the left edge of a redaction, it's ambiguous whether the inserted text should be
        # redacted or not. The above code does redact it, but it's more often correct not to. This unredacts the insertion,
        # converting [["redact"],["ocr"],["edit",{"was": ""}],"\u00ad",["/edit"]] to
        # [["edit",{"was": ""}],"\u00ad",["/edit"],["redact"],["ocr"]]
        have_text = False  # we only perform this fix after seeing some text in the paragraph
        for block in blocks:
            for i in range(len(block)-4):
                token = block[i]
                if not have_text:
                    if type(token) == str:
                        have_text = True
                    continue
                if (
                        token == ['redact']
                        and type(block[i+1]) != str and block[i+1][0] == 'ocr'
                        and type(block[i+2]) != str and block[i+2][0] == 'edit' and block[i+2][1]['was'] == ''
                        and type(block[i+3]) == str
                        and block[i+4] == ['/edit']
                ):
                    block[i:i+5] = block[i+2:i+5] + block[i:i+2]

def extract_paragraphs(children, case_id_to_alto_ids, blocks_by_id):
    """
        Extract paragraph and footnote structures from a list of CaseMETS paragraphs and footnotes as PyQuery elements.

        Example:
        >>> doc = PyQuery("<opinion><author id='1'>text</author><footnote id='footnote_1_1'><p id='2'>footnote text</p></footnote></opinion>")
        >>> case_id_to_alto_ids = {'1': [1], 'footnote_1_1': [1], '2': [1]}
        >>> blocks_by_id = {1: {}}
        >>> paragraphs, footnotes, paragraph_els = extract_paragraphs(doc.children().items(), case_id_to_alto_ids, blocks_by_id)
        >>> assert paragraphs == [{'id': '1', 'class': 'author', 'block_ids':[1]}]
        >>> assert footnotes == [{'id': 'footnote_1_1', 'paragraphs': [{'block_ids': [1], 'id': '2', 'class': 'p'}]}]
        >>> assert paragraph_els == [doc('author'), doc('p')]
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
        diff = '\n'.join(difflib.ndiff([e1.text or ''], [e2.text or '']))
        raise ValueError("e1.text != e2.text:\n%s" % diff)
    if e1.tail != e2.tail:
        raise ValueError("e1.tail != e2.tail (%s != %s)" % (e1.tail, e2.tail))
    ignore_attrs = ignore.get('attrs', set()) | ignore.get('tag_attrs', {}).get(e1.tag.rsplit('}', 1)[-1], set())
    e1_attrib = {k:v for k,v in e1.attrib.items() if k not in ignore_attrs}
    e2_attrib = {k:v for k,v in e2.attrib.items() if k not in ignore_attrs}
    if e1_attrib != e2_attrib:
        diff = "\n".join(difflib.Differ().compare(["%s: %s" % i for i in sorted(e1_attrib.items())], ["%s: %s" % i for i in sorted(e2_attrib.items())]))
        raise ValueError("e1.attrib != e2.attrib:\n%s" % diff)
    s1 = [i for i in e1 if i.tag.rsplit('}', 1)[-1] not in ignore.get('tags', ())]
    s2 = [i for i in e2 if i.tag.rsplit('}', 1)[-1] not in ignore.get('tags', ())]
    if len(s1) != len(s2):
        diff = "\n".join(difflib.Differ().compare([s.tag for s in s1], [s.tag for s in s2]))
        raise ValueError("e1 children != e2 children:\n%s" % diff)
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
        duplicates=page.get('duplicates') or None,
        extra_redacted_ids=page.get('extra_redacted_ids') or None,
        image_file_name=page['file_name'],
        width=page['width'],
        height=page['height'],
        deskew=page['deskew'],
        font_names=page['font_names'],
        ingest_source=ingest_source,
        ingest_path=page['path'],
    )

def strip_bracketnum_hyphens(text):
    """
        Tags like <bracketnum>[4---]</bracketnum> mess up our process because some of the hyphens get redacted and some
        get edited out. We end up editing out the redacted one and letting an unredacted hyphen slip through. Since
        hyphens next to the bracket are typos anyway, filter them out. Note that hyphens not touching the brackets are
        ok and not stripped out, like <bracketnum>[4-8]</bracketnum>.
    """
    text = re.sub(r'\[[-\xad]+', '[', text)
    text = re.sub(r'[-\xad]+]', ']', text)
    return text

def conform_cc_attr(parsed):
    """ Older volumes have character confidence stored as '100,100,100,100' instead of '0000'. Switch back. """
    for string_el in parsed('String[CC]'):
        cc = string_el.attrib['CC']
        # bail out if we get passed a new-style file by mistake:
        if set(cc) == {'0', '9'}:
            break
        string_el.attrib['CC'] = "".join('0' if i == '100' else '9' for i in cc.split(","))

def infer_cc_style(parsed):
    """ Guess whether alto file has old-style CC tags like '100,100,100,100' instead of new-style like '0000'. """
    for string_el in parsed('String[CC]'):
        cc_chars = set(string_el.attrib['CC'])
        if cc_chars & {'1', ','}:  # old-style if CC tag contains a 1 or ,
            return True
        if cc_chars == {'0', '9'}:  # new-style if CC tag contains only 0 or 9
            return False
    return None

def block_text(block):
    """ Return raw text of block. """
    return "".join(token for token in block.get('tokens', []) if type(token) == str)

def assert_reversability(volume_barcode, unredacted_storage, redacted_storage,
                         volume, pages, cases, fonts_by_id, text_replacements={},
                         paths=None, blocks_by_id=None, key=settings.REDACTION_KEY, catch_validation_errors=False):
    """
        Check that our extraction task has succeeded, by making sure that the volume, page, cases, and fonts_by_id
        variables can be used to recreate the files in unredacted_storage and redacted_storage.
    """
    # setup
    paths = paths or files_by_type(sorted(unredacted_storage.iter_files_recursive()))
    blocks_by_id = blocks_by_id or {block['id']: block for page in pages for block in page['blocks']}

    # decrypt again
    if redacted_storage:
        print("Decrypting pages")
        for page in pages:
            page_obj = PageStructure(blocks=page['blocks'], encrypted_strings=page['encrypted_strings'])
            page_obj.decrypt(key)
            
    ### validate results
    # Here we build fake Django objects and make sure we can render the extracted data back into XML that matches
    # the source files.
    renderer = render_case.VolumeRenderer(blocks_by_id, fonts_by_id, {}, pretty_print=False)  # we don't need labels_by_block_id because original_xml cases don't include page numbers

    redacted_errors_as_warnings = catch_validation_errors or 'tool_version_mismatch' in volume['metadata'].get('errors', {}) or volume_barcode in skip_redacted_validation

    ## validate volume dict
    volume_obj = VolumeMetadata(barcode=volume_barcode, xml_metadata=volume['metadata'])
    new_xml = renderer.render_volume(volume_obj)
    parsed = parse(unredacted_storage, paths['volume'][0])
    volume_el = parsed('volume')
    old_xml = str(volume_el)
    old_xml = re.sub(r'\s*(<[^>]+>)\s*', r'\1', old_xml, flags=re.S)  # strip whitespace around elements
    old_xml = old_xml.replace('<nominativereporter abbreviation="" volnumber=""/>', '')  # remove blank <normativereporter>
    old_xml = re.sub(r'\s+', ' ', old_xml)  # normalize multiple spaces
    xml_strings_equal(new_xml, old_xml)
    
    ## validate pages dict
    print("Checking ALTO integrity")

    # validate everything *except* the attributes listed here, which are permanently stripped:
    ignore = {
        'tag_attrs': {
            'Page': {'ID', 'PHYSICAL_IMG_NR', 'xmlns'},
            'PrintSpace': {'ID'},
            'TextBlock': {'TAGREFS'},
            'Illustration': {'TAGREFS'},
            'TextLine': {'ID'},
            'String': {'ID', 'TAGREFS'},
            'SP': {'HPOS', 'ID', 'VPOS', 'WIDTH'}
        }
    }
    if 'skip_cc_check' in volume:
        ignore['tag_attrs']['String'].update(('WC', 'CC'))

    for page in pages:
        page_obj = create_page_obj(volume_obj, page)
        to_test = [(unredacted_storage, page['path'], False)]
        if redacted_storage:
            to_test.append((redacted_storage, page['path'].replace('unredacted', 'redacted'), True))
        for storage, path, redacted in to_test:
            print("- checking %s" % path)
            if path in skip_validation_files:
                continue
            if redacted and 'duplicates' in page:
                print(" - skipping redacted test; page has duplicates")
                continue
            parsed = parse(storage, path, text_replacements=text_replacements)
            parsed('SP:first-child,SP:last-child').remove()  # remove <SP> element from start and end of <TextLine> -- can happen because of redaction

            # remove elements from page['extra_redacted_ids'], as well as parent TextLine if it ends up empty
            if redacted and 'extra_redacted_ids' in page:
                for redacted_id in page['extra_redacted_ids']:
                    el = parsed('[ID="%s"]' % redacted_id)
                    parent = el.parent()
                    parsed('[ID="%s"]' % redacted_id).remove()
                    if parent and len(parent[0]) == 0:
                        parent.remove()

            # fix old CC attributes
            if 'old_cc_style' in page:
                conform_cc_attr(parsed)

            # strip spaces from <String> elements CONTENT and CC tags to match stripping in ingest
            for s in parsed('String'):
                content = s.attrib['CONTENT']
                if content != content.strip():
                    pre_space, post_space = re.match(r'(\s*).*?(\s*)$', content).groups()
                    s.attrib['CONTENT'] = content[len(pre_space):-len(post_space) or None]
                    s.attrib['CC'] = s.attrib['CC'][len(pre_space):-len(post_space) or None]

            alto_xml_output = renderer.render_page(page_obj, redacted)
            original_alto = str(parsed('Page'))
            original_alto = original_alto.replace('WC="1.0"', 'WC="1.00"')  # normalize irregular decimal places
            original_alto = original_alto.replace('CC=""', 'CC="0"')  # normalize character confidence for empty strings -- some are CC="", some are CC="0"

            try:
                xml_strings_equal(alto_xml_output, original_alto, ignore)
            except ValueError as e:
                if redacted and redacted_errors_as_warnings:
                    volume['metadata'].setdefault('errors', {}).setdefault('failed_validations', {})[path] = True
                    print("- ignoring validation error in %s" % path)
                else:
                    raise
            
    # validate cases
    print("Checking case integrity")
    for case in cases:
        # create fake CaseMetadata object
        case_obj = CaseMetadata(case_id=case['id'], volume=volume_obj, duplicative=case['metadata']['duplicative'],
                                first_page=case['metadata']['first_page'], last_page=case['metadata']['last_page'])
        case_obj.structure = CaseStructure(metadata=case_obj, opinions=case['opinions'])
        case_obj.initial_metadata = CaseInitialMetadata(case=case_obj, metadata=case['metadata'])

        to_test = [(unredacted_storage, case['path'], False)]
        if redacted_storage:
            to_test.append((redacted_storage, case['path'].replace('unredacted', 'redacted'), True))

        for storage, path, redacted in to_test:
            # load comparison xml
            print("- checking %s" % path)
            if path in skip_validation_files:
                continue
            if redacted and 'has_corrupt_blocks' in case['metadata']:
                print(" - skipping redacted test; case has corrupt blocks")
                continue
            parsed = parse(storage, path, remove_namespaces=False, text_replacements=text_replacements)
            CaseXML.reorder_head_matter(parsed)
            parsed = parsed.remove_namespaces()
            # strip hyphens from <bracketnum> to match ingested case
            for headnote_ref in parsed('casebody bracketnum').items():
                headnote_ref.text(strip_bracketnum_hyphens(headnote_ref.text()))

            ## compare <casebody>
            renderer.redacted = redacted
            new_casebody = renderer.render_orig_xml(case_obj)
            old_casebody = str(parsed('casebody'))
            casebodies = [new_casebody, old_casebody]

            # normalize formatting in casebody xml
            strip_whitespace_els = 'blockquote|author|p|headnotes|history|disposition|syllabus|summary|attorneys|judges|otherdate|decisiondate|parties|seealso|citation|docketnumber|court|correction'
            for i, casebody in enumerate(casebodies):
                casebody = casebody.replace(' label=""', '')  # footnote with empty label
                casebody = re.sub(r'>\s+<', '><', casebody)  # normalize multiline xml file to single file
                casebody = re.sub(r'<([a-z]+)[^>]*></\1>', '', casebody)  # remove empty elements (typically redacted paragraphs)
                casebody = re.sub(r'\s+', ' ', casebody)  # normalize multiple spaces
                # remove whitespace from start and end of tags:
                casebody = re.sub(r'(<(?:%s)[^>]*>)\s+' % strip_whitespace_els, r'\1', casebody, flags=re.S)
                casebody = re.sub(r'\s+(</(?:%s)>)' % strip_whitespace_els, r'\1', casebody, flags=re.S)
                casebody = casebody.replace('\xad ', '\xad')  # fix doubled-paragraph bug
                casebodies[i] = casebody

            try:
                xml_strings_equal(*casebodies, {
                    'attrs': {'pgmap', 'xmlns'},
                    'tag_attrs': {
                        'footnote': {'redact'},  # the redact attr isn't reliably set in the original, so our output may not match. comparison will still ensure that redacted footnotes don't appear.
                    }
                })
            except ValueError as e:
                if redacted and redacted_errors_as_warnings:
                    volume['metadata'].setdefault('errors', {}).setdefault('failed_validations', {})[path] = True
                    print("- ignoring validation error in %s" % path)
                else:
                    raise

            ## compare <case>
            if not case_obj.duplicative:
                case_heads = [
                    renderer.render_case_header(case_obj.case_id, case_obj.initial_metadata.metadata),
                    str(parsed('case'))
                ]
                for i, case_head in enumerate(case_heads):
                    case_head = case_head.replace('<docketnumber/>', '')
                    case_head = case_head.replace('&#13;', ' ')  # normalize \r
                    case_head = re.sub(r'\s*(<[^>]+>)\s*', r'\1', case_head, flags=re.S)  # strip whitespace around elements
                    case_head = re.sub(r'\s+', ' ', case_head)  # normalize multiple spaces within elements
                    case_heads[i] = case_head

                try:
                    xml_strings_equal(*case_heads)
                except ValueError as e:
                    if redacted and redacted_errors_as_warnings:
                        volume['metadata'].setdefault('errors', {}).setdefault('failed_validations', {})[path] = True
                        print("- ignoring validation error in %s" % path)
                    else:
                        raise

@shared_task
def volume_to_json(volume_barcode, primary_path, secondary_path, key=settings.REDACTION_KEY, save_failed=False, catch_validation_errors=False):
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
                    volume_to_json_inner(volume_barcode, unredacted_storage, redacted_storage, key, save_failed, catch_validation_errors)
            else:
                volume_to_json_inner(volume_barcode, unredacted_storage, None, key, save_failed, catch_validation_errors)
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

def volume_to_json_inner(volume_barcode, unredacted_storage, redacted_storage=None, key=settings.REDACTION_KEY, save_failed=False, catch_validation_errors=False):
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
    if volume_barcode in skip_redacted_validation:
        volume['metadata'].setdefault('errors', {})['manual_skip_redacted_validation'] = True

    # extract data from comments like <!--Created by Innodata R.E.D. RLI tool version 20151218-103 on 2015-12-22T16:41:08.081941-->
    processing = metadata['processing'] = {}
    processing['tool_version'], processing['date'] = parsed('mets')[0][0].text.split('RLI tool version ', 1)[1].split('-->', 1)[0].split(' on ')
    if redacted_storage:
        redacted_parsed = parse(redacted_storage, paths['volume'][0].replace('unredacted', 'redacted'))
        processing['redacted_tool_version'], processing['redacted_date'] = redacted_parsed('mets')[0][0].text.split('RLI tool version ', 1)[1].split('-->', 1)[0].split(' on ')
        if processing['tool_version'] != processing['redacted_tool_version']:
            volume['metadata'].setdefault('errors', {})['tool_version_mismatch'] = True

    ### Extract data for each page into the pages dict ###

    print("Reading ALTO files")
    fake_font_id = 1
    fonts_by_id = {}
    text_replacements = {}
    corrupt_blocks = set()
    old_cc_style = None
    for path in paths['alto']:
        print(path)

        parsed = parse(unredacted_storage, path)
        alto_id = 'alto_' + path.split('_ALTO_', 1)[1].split('.')[0]

        # check if we need to fix CC attributes
        if old_cc_style is None:
            old_cc_style = infer_cc_style(parsed)
        if old_cc_style:
            conform_cc_attr(parsed)
            volume['metadata'].setdefault('errors', {})['old_cc_style'] = True

        # index rects in unredacted file
        unredacted_rects = defaultdict(list)
        for block in parsed('TextBlock,Illustration,String'):
            unredacted_rects[(block.tag, rect(block.attrib))].append(block.attrib['ID'])

        # record duplicates and mark blocks as corrupted if they appear more than once
        duplicates = []
        for tag_rect, ids in unredacted_rects.items():
            if len(ids) > 1:
                duplicates.append([tag_rect, ids])
                if tag_rect[0] == 'String':
                    ids = {parsed('[ID="%s"]' % id).parent().parent().attr.ID for id in ids}
                corrupt_blocks.update(ids)

        # load redacted file and determine which IDs appear in the redacted version
        redacted_ids = set()
        if redacted_storage:
            # index rects in redacted file
            redacted_path = path.replace('unredacted', 'redacted')
            redacted_parsed = parse(redacted_storage, redacted_path)
            redacted_rects = defaultdict(list)
            for block in redacted_parsed('TextBlock,Illustration,String'):
                redacted_rects[(block.tag, rect(block.attrib))].append(block.attrib['ID'])

            for tag_rect, ids in unredacted_rects.items():
                # redact rects if they appear more frequently in unredacted version
                if len(ids) != len(redacted_rects[tag_rect]):
                    redacted_ids.update(ids)

            # check if redacted volume was created later and has corrected CC values
            # if so, build a lookup to populate WC and CC from redacted file, and skip validation of those attrs
            if old_cc_style:
                redacted_old_cc_style = infer_cc_style(redacted_parsed)
                if not redacted_old_cc_style:
                    volume['skip_cc_check'] = True
                    cc_lookup = {(el.attrib['ID'], el.attrib['CONTENT']):(el.attrib['WC'], el.attrib['CC']) for el in redacted_parsed('String')}

        # build lookup of block labels (e.g. name, p, blockquote) by tagref ID
        labels_by_tagref = {s.attrib['ID']: s.attrib['LABEL'] for s in parsed[0].iter('StructureTag')}

        page_el = parsed('Page')
        page = {
            'id': alto_id,
            'path': str(path),
            'order': int(page_el.attr.ID.split("_")[1]),
            'width': int(page_el.attr.WIDTH),
            'height': int(page_el.attr.HEIGHT),
            'file_name': parsed('sourceImageInformation fileName').text().replace('.png', '.tif'),
            'deskew': parsed('processingStepSettings').text(),
            'innodata_timestamp': parsed('alto')[0][0].text.rsplit(': ', 1)[-1],  # not actually saving this since it's redundant of volume['metadata']['processing']
            'spaces': [],
            'blocks': [],
        }

        # volume barcodes containing underscore, like "Cal5th_001", may have file_name incorrectly as
        # Cal5th_00100196_1.tif instead of Cal5th_001_00100196_1.tif. Detect and fix:
        if not unredacted_storage.exists(page['file_name']):
            fixed_file_name = fix_image_file_name(volume_barcode, page['file_name'])
            if unredacted_storage.exists('images/'+fixed_file_name):
                page['file_name'] = fixed_file_name

        if duplicates:
            page['duplicates'] = duplicates
            volume['metadata'].setdefault('errors', {})['duplicate_blocks'] = True

        if old_cc_style:
            page['old_cc_style'] = True

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

        # mark footnotemarks and bracketnums
        # <RoleTag ID="footnotemark0001" LABEL="footnotemark"/>
        # <RoleTag ID="bracketnum0001" LABEL="bracketnum"/>
        extra_redacted_ids = []
        for role_tag in parsed('RoleTag[LABEL="footnotemark"],RoleTag[LABEL="bracketnum"]'):
            tags = parsed('[TAGREFS~="%s"]' % role_tag.attrib['ID'])
            # these won't be found if a single word contains more than one footnotemark, in which case we can't do
            # anything useful -- just skip
            if not tags:
                continue
            start_tag, end_tag = tags[0], tags[-1]
            tag_label = role_tag.attrib['LABEL']
            start_tag.attrib['prefix_char'] = tag_marker_lookup[tag_label]
            end_tag.attrib['suffix_char'] = tag_marker_lookup['/'+tag_label]

            # redact any ALTO tags inside a redacted tag
            if redacted_storage and tags.length > 1 and start_tag.attrib['ID'] in redacted_ids:

                # if multiple tags have same rect, bail out -- we can't apply this logic to a file with duplicate blocks
                rects = set(rect(tag.attrib) for tag in tags)
                if len(rects) < len(tags):
                    continue

                tag = start_tag
                while True:
                    next_tag = tag.getnext()
                    if next_tag is None:

                        space_before_start = start_tag.getprevious()
                        if space_before_start is not None:
                            tag_id = space_before_start.attrib['ID']
                            if tag_id not in redacted_ids:
                                redacted_ids.add(tag_id)
                                extra_redacted_ids.append(tag_id)

                        parent_tag = tag.getparent()
                        next_line = parent_tag.getnext()
                        if next_line is None:
                            next_tag = parent_tag.getparent().getnext()[0][0]
                        else:
                            next_tag = next_line[0]
                    tag = next_tag
                    if tag == end_tag:
                        break
                    tag_id = tag.attrib['ID']
                    if tag_id not in redacted_ids:
                        redacted_ids.add(tag_id)
                        extra_redacted_ids.append(tag_id)
        if len(extra_redacted_ids) > 1:
            print("extra_redacted_ids:", extra_redacted_ids)
            page['extra_redacted_ids'] = extra_redacted_ids

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
            if space_rect == (0, 0, page['width'], page['height']):
                space_index = None
            else:
                page['spaces'].append(space_rect)
                space_index = len(page['spaces']) - 1

            # Extract each <TextBlock>:
            for block_el in space_el[0]:
                block_rect = rect(block_el.attrib)
                block = {
                    'id': block_el.attrib['ID'],
                    'rect': block_rect,
                    'class': labels_by_tagref[block_el.attrib['TAGREFS']],
                }

                # mark corrupt blocks
                if block['id'] in corrupt_blocks:
                    block['corrupt'] = True

                # annotate blocks that have an atypical PrintSpace (if there are any)
                if space_index is not None:
                    block['space'] = space_index

                # check for redacted blocks
                if redacted_storage:
                    if block['id'] in redacted_ids:
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
                    check_string_redaction = redacted_storage and not block.get('redacted', False)
                    first_string = True
                    in_redacted_tag = False

                    # handle <TextLine>
                    for line_el in block_el.iter('TextLine'):
                        redacted_span = False
                        line_rect = rect(line_el.attrib)
                        tokens.append(['line', {'rect': line_rect}])

                        # handle <String>
                        for string in line_el.iter('String'):
                            string_attrib = string.attrib  # for speed
                            string_rect = rect(string_attrib)

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
                                    if string_attrib['ID'] not in redacted_ids and not in_redacted_tag:
                                        tokens.append(['/redact'])
                                        redacted_span = False
                                else:
                                    if string_attrib['ID'] in redacted_ids:
                                        tokens.append(['redact'])
                                        redacted_span = True

                            # Write an ['ocr', {'rect':<bounding box>, 'wc':<word confidence>, 'cc':<character confidence>}]
                            # span for each word.
                            text = string_attrib['CONTENT']
                            if old_cc_style and cc_lookup and (string_attrib['ID'], text) in cc_lookup:
                                wc, cc = cc_lookup[string_attrib['ID'], text]
                            else:
                                wc = string_attrib['WC']
                                cc = string_attrib['CC']
                            ocr_token = ['ocr', {'rect': string_rect, 'wc': float(wc)}]

                            # cc is a string of zeroes for each high-confidence character and nines for each low-confidence
                            # character. We don't store all-zero strings at all. For strings with some nines, convert to
                            # binary and interpret as an integer for compactness.
                            if '9' in cc:
                                if text != text.strip():
                                    # If we're storing cc and text has whitespace, we have to strip the same character range from both text and cc:
                                    pre_space, post_space = re.match(r'(\s*).*?(\s*)$', text).groups()
                                    text = text[len(pre_space):-len(post_space) or None]
                                    cc = cc[len(pre_space):-len(post_space) or None]
                                if cc:
                                    ocr_token[1]['cc'] = int(cc.replace('9', '1'), 2)
                            else:
                                # If not storing cc, just strip whitespace from text:
                                text = text.strip()

                            # Append prefix and suffix tag chars, if any -- these mark where footnote/bracket tags start
                            # and stop for later diffing with case text
                            if 'prefix_char' in string_attrib:
                                text = string_attrib['prefix_char'] + text
                                in_redacted_tag = redacted_span
                            if 'suffix_char' in string_attrib:
                                text = text + string_attrib['suffix_char']
                                in_redacted_tag = False

                            # Append a space if next tag is a space, or if string does not end with a hyphen.
                            next_tag = string.getnext()
                            if (next_tag is not None and next_tag.tag == 'SP') or (text and text[-1] not in ('-', '\xad')):
                                text += ' '

                            # add [['ocr'], text, ['/ocr']]
                            if redacted_span and 'suffix_char' in string_attrib and text and text[-1] == ' ' and not first_string:
                                # don't redact space after footnote
                                tokens.extend((ocr_token, text[:-1], ['/redact'], ' ', ['redact'], ['/ocr']))
                            elif text:
                                # <String CONTENT> can be empty, so only include text if it's filled in:
                                tokens.extend((ocr_token, text, ['/ocr']))
                            else:
                                tokens.extend((ocr_token, ['/ocr']))

                            first_string = False

                        # close open [redact]
                        if redacted_span:
                            tokens.append(['/redact'])

                        tokens.append(['/line'])

                    # close open [font]
                    if last_font:
                        tokens.append(['/font'])

                page['blocks'].append(block)

        # reverse the text replacements so we first change BL_1.2 to BL_1.3, and then BL_1.1 to BL_1.2:
        if redacted_storage and redacted_path in text_replacements:
            text_replacements[redacted_path].reverse()

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

        # check for corrupt blocks
        duplicates = []
        for alto_ids in case_id_to_alto_ids.values():
            if any(id in corrupt_blocks for id in alto_ids):
                metadata['has_corrupt_blocks'] = True
            if len(alto_ids) == 2:
                texts = [re.sub(r'\s+', ' ', block_text(blocks_by_id[id]).replace('\xad', '').replace('-', '').strip()) for id in alto_ids]
                if texts[0] == texts[1]:
                    duplicates.append(alto_ids)
        if duplicates:
            metadata['duplicates'] = duplicates
            volume['metadata'].setdefault('errors', {})['doubled_paragraphs'] = True

        # extract each <opinion> from the <casebody> for processing
        if duplicative:
            # for duplicative cases, create fake <opinion> with direct children of <casebody>, with type 'unprocessed'
            sections = [['unprocessed', casebody.children().items()]]
        else:
            # for non-duplicative case, create fake <opinion> with elements appearing before first opinion, type 'head'
            head_matter_children = casebody.children(':not(opinion):not(correction)').items()
            opinion_els = [[el.attr.type, list(el.children().items())] for el in casebody.children('opinion').items()]
            sections = [['head', list(head_matter_children)]] + opinion_els

            # handle <correction> tags after last opinion
            corrections = list(casebody.children('correction').items())
            if corrections:
                sections.append(['corrections', corrections])

            # add 'ref' attribute to each <bracketnum>, linking to ID of each <headnotes> element if possible
            headnotes_lookup = {}
            for headnote in casebody('headnotes').items():
                number = re.match(r'\d+', headnote.text())
                if number:
                    headnotes_lookup[number.group(0)] = headnote.attr.id
            for headnote_ref in casebody('bracketnum').items():
                headnote_ref.text(strip_bracketnum_hyphens(headnote_ref.text()))
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

        # if we have text_replacements for pages this case depends on, also apply them to this case:
        if text_replacements:
            redacted_path = path.replace('unredacted', 'redacted')
            for page_ref in parsed('fileGrp[USE="alto"] FLocat'):
                page_path = page_ref.attrib['{http://www.w3.org/1999/xlink}href'][3:]
                if page_path in text_replacements:
                    text_replacements.setdefault(redacted_path, []).append(text_replacements[page_path])

        cases.append(case)

    # fix tag markers from ALTO blocks not included in cases
    print("Fixing non-case ALTO tags")
    case_blocks = {block_id for case in cases for par in iter_pars(case['opinions']) for block_id in par['block_ids']}
    for page in pages:
        for block in page['blocks']:
            if block['id'] not in case_blocks:
                tokens = block.get('tokens', [])
                if tokens:
                    for i in range(len(tokens)-1, -1, -1):
                        token = tokens[i]
                        if type(token) == str and tag_marker_re.search(token):
                            parts = tag_marker_re.split(token)
                            tokens[i:i+1] = [[tag_name_lookup[p]] if p in tag_name_lookup else p for p in parts]

    # encrypt redacted strings
    if redacted_storage:
        print("Encrypting pages")
        for page in pages:
            page_obj = PageStructure(blocks=page['blocks'])
            page_obj.encrypt(key)
            page['encrypted_strings'] = page_obj.encrypted_strings

    ### export results to a temp file


    font_attrs = ['family', 'size', 'style', 'type', 'width']
    fonts_by_id = {f.id: {attr: getattr(f, attr) for attr in font_attrs} for f in fonts_by_id.values()}
    with tempfile.SpooledTemporaryFile(max_size=2**20*100) as temp_output_file:

        # do this here so we can safely decrypt again for validation
        zip = ZipFile(temp_output_file, 'w', compression=ZIP_BZIP2)
        for path, obj in (('pages.json', pages), ('cases.json', cases), ('fonts.json', fonts_by_id)):
            zip.writestr(path, json.dumps(obj))

        ### check reversability ###

        try:
            assert_reversability(
                volume_barcode, unredacted_storage, redacted_storage,
                volume, pages, cases, fonts_by_id, text_replacements,
                paths, blocks_by_id, key, catch_validation_errors)
        except:
            # save temp zip locally if requested
            if save_failed:
                dest_path = Path(settings.BASE_DIR, 'test_data/zips', 'token_streams', unredacted_storage.path.name + '-failed.zip')
                print("Copying failed zip to %s" % dest_path)
                zip.writestr('volume.json', json.dumps(volume))
                zip.close()
                temp_output_file.seek(0)
                with dest_path.open('wb') as out:
                    shutil.copyfileobj(temp_output_file, out)
            raise

        # add volume.json here so we get any errors recorded during validation
        zip.writestr('volume.json', json.dumps(volume))
        zip.close()
        temp_output_file.seek(0)

        ### copy temp file to permanent storage

        out_path = Path('token_streams', unredacted_storage.path.name + '.zip')
        print("Writing temp files to %s" % out_path)
        if captar_storage.exists(str(out_path)):
            captar_storage.delete(str(out_path))
        captar_storage.save(str(out_path), temp_output_file)

### validate_token_stream fab task

def test_reversability(volume_barcode, key=settings.REDACTION_KEY):
    """
        This does just the last step of volume_to_json, by loading up the files for a given barcode and running
        assert_reversability. This separate task is mostly useful for quickly debugging a -failed.zip file created
        by a previous run of volume_to_json.
    """
    redacted_paths = list(captar_storage.iter_files('redacted/%s' % volume_barcode, partial_path=True))
    unredacted_paths = list(captar_storage.iter_files('unredacted/%s' % volume_barcode, partial_path=True))
    if unredacted_paths:
        unredacted_storage = CaptarStorage(captar_storage, unredacted_paths[-1])
        redacted_storage = CaptarStorage(captar_storage, redacted_paths[-1])
    else:
        unredacted_storage = CaptarStorage(captar_storage, redacted_paths[-1])
        redacted_storage = None
    zip_path = list(i for i in captar_storage.iter_files('token_streams/%s' % volume_barcode, partial_path=True) if i.endswith('.zip'))
    with captar_storage.open(zip_path[-1], 'rb') as raw:
        with ZipFile(raw) as zip:
            volume = json.loads(zip.open('volume.json').read().decode('utf8'))
            pages = json.loads(zip.open('pages.json').read().decode('utf8'))
            cases = json.loads(zip.open('cases.json').read().decode('utf8'))
            fonts_by_id = {int(k):v for k,v in json.loads(zip.open('fonts.json').read().decode('utf8')).items()}
    for page in pages:
        page['font_names'] = {int(k):v for k, v in page['font_names'].items()}
    assert_reversability(volume_barcode, unredacted_storage, redacted_storage,
                         volume, pages, cases, fonts_by_id,
                         key=key)

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
            cases = json.loads(zip.open('cases.json').read().decode('utf8').replace('\xad', ''))
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

        # in the token stream data structure, volume_number is stored under reporter, so it doesn't make it to the
        # volume metadata unless explicitly set.
        if not volume_obj.volume_number and \
                'volume_number' in volume['metadata']['reporter'] and \
                volume['metadata']['reporter']['volume_number']:
            volume_obj.volume_number = volume['metadata']['reporter']['volume_number']
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
            case_objs.append(CaseStructure(metadata=metadata_obj, opinions=case['opinions'], ingest_source=ingest_source, ingest_path=case['path']))
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
