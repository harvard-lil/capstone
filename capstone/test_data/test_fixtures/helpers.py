import difflib
import hashlib
import os
from pathlib import Path

from scripts.helpers import parse_xml, parse_html


def file_hash(path):
    """
        Return md5 hash of file contents.
    """
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

def dir_hash(directory):
    """
        Return single md5 hash of all filenames and file contents in directory, for comparison.
    """
    hash = hashlib.md5()
    path = Path(directory)

    if not path.exists():
        raise FileNotFoundError

    for file in sorted(path.glob('**/*')):
        hash.update(bytes(str(file), 'utf8'))
        if file.is_file():
            hash.update(file.read_bytes())

    return hash.hexdigest()

def elements_equal(e1, e2, ignore={}, ignore_trailing_whitespace=False, tidy_style_attrs=False, exc_class=ValueError):
    """
        Recursively compare two lxml Elements.
        Raise an exception (by default ValueError) if not identical.
        Optionally, ignore trailing whitespace after block elements.
        Optionally, munge "style" attributes for easier comparison.
    """
    if e1.tag != e2.tag:
        raise exc_class("e1.tag != e2.tag (%s != %s)" % (e1.tag, e2.tag))
    if e1.text != e2.text:
        diff = '\n'.join(difflib.ndiff([e1.text or ''], [e2.text or '']))
        raise exc_class("e1.text != e2.text:\n%s" % diff)
    if e1.tail != e2.tail:
        exc = exc_class("e1.tail != e2.tail (%s != %s)" % (e1.tail, e2.tail))
        if ignore_trailing_whitespace:
            if (e1.tail or '').strip() or (e2.tail or '').strip():
                raise exc
        else:
            raise exc
    ignore_attrs = ignore.get('attrs', set()) | ignore.get('tag_attrs', {}).get(e1.tag.rsplit('}', 1)[-1], set())
    e1_attrib = {k:v for k,v in e1.attrib.items() if k not in ignore_attrs}
    e2_attrib = {k:v for k,v in e2.attrib.items() if k not in ignore_attrs}
    if tidy_style_attrs and e1_attrib.get('style'):
        # allow easy comparison of sanitized style tags by removing all spaces and final semicolon
        e1_attrib['style'] = e1_attrib['style'].replace(' ', '').rstrip(';')
        e2_attrib['style'] = e2_attrib['style'].replace(' ', '').rstrip(';')
    if e1_attrib != e2_attrib:
        diff = "\n".join(difflib.Differ().compare(["%s: %s" % i for i in sorted(e1_attrib.items())], ["%s: %s" % i for i in sorted(e2_attrib.items())]))
        raise exc_class("e1.attrib != e2.attrib:\n%s" % diff)
    s1 = [i for i in e1 if i.tag.rsplit('}', 1)[-1] not in ignore.get('tags', ())]
    s2 = [i for i in e2 if i.tag.rsplit('}', 1)[-1] not in ignore.get('tags', ())]
    if len(s1) != len(s2):
        diff = "\n".join(difflib.Differ().compare([s.tag for s in s1], [s.tag for s in s2]))
        raise exc_class("e1 children != e2 children:\n%s" % diff)
    for c1, c2 in zip(s1, s2):
        elements_equal(c1, c2, ignore, ignore_trailing_whitespace, tidy_style_attrs, exc_class)

    # If you've gotten this far without an exception, the elements are equal
    return True


def xml_equal(s1, s2, **kwargs):
    e1 = parse_xml(s1)[0]
    e2 = parse_xml(s2)[0]
    return elements_equal(e1, e2, **kwargs)


def html_equal(s1, s2, **kwargs):
    e1 = parse_html(s1)[0]
    e2 = parse_html(s2)[0]
    return elements_equal(e1, e2, **kwargs)


def get_timestamp(case):
    from capdb.models import CaseLastUpdate
    [[t]] = CaseLastUpdate.objects.filter(case_id=case.id).values_list('timestamp')
    return t


def check_timestamps_changed(case, timestamp):
    new_t = get_timestamp(case)
    assert timestamp < new_t
    return new_t


def check_timestamps_unchanged(case, timestamp):
    assert get_timestamp(case) == timestamp


def set_case_text(case, text, text2="", text3=None):
    """Set text of blocks defined in PageStructureFactory."""
    page = case.structure.pages.first()
    page.blocks[1]["tokens"][3] = text
    page.blocks[2]["tokens"][3] = text2
    if text3 is not None:
        page.blocks[3]["tokens"][3] = text3
    page.save()


def sort_nested_dict(d):
    """Alphabetize keys in nested dict, including dicts inside lists."""
    if isinstance(d, dict):
        return {k: sort_nested_dict(v) for k, v in sorted(d.items())}
    if isinstance(d, (list, tuple)):
        return [sort_nested_dict(v) for v in d]
    return d


def current_test_name():
    return os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0]


def check_path(pytestconfig, new_contents, saved_path):
    """
    Either report a diff between new_contents and saved_path, or update saved_path to match new_contents, depending on pytest --recreate_files.
    """
    if isinstance(new_contents, Path):
        new_contents = new_contents.read_text()
    old_contents = saved_path.read_text() if saved_path.exists() else ''
    if new_contents != old_contents:
        if pytestconfig.getoption('recreate_files'):
            saved_path.parent.mkdir(parents=True, exist_ok=True)
            saved_path.write_text(new_contents)
        elif old_contents:
            assert new_contents == old_contents, f"File {saved_path} has changed. Run pytest -k {current_test_name()} --recreate_files to update."
        else:
            assert False, f"File {saved_path} does not exist. Run pytest -k {current_test_name()} --recreate_files to update."
