from distutils.dir_util import copy_tree
from pathlib import Path
import pytest
import yaml
from pyquery import PyQuery

from django.conf import settings
from django.core import management
from django.forms import model_to_dict

from capdb.models import VolumeMetadata, Citation
from capdb.tasks import update_elasticsearch_from_queue
from fabfile import refresh_case_body_cache
from scripts.fastcase import ingest_fastcase
from scripts.fastcase.format_fastcase import segment_paragraphs
from test_data.test_fixtures.helpers import sort_nested_dict, check_path


@pytest.mark.parametrize("input,expected", [
    # remove the extra <p> if the previous word ends in continuation_chars and the previous and next tags match:
    ("<p>foo</p><p>[935 F.3d 745]</p><p>bar</p>",
     '<p>foo <a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a>bar</p>'),
    ("<blockquote>foo</blockquote><p>[935 F.3d 745]</p><blockquote>bar</blockquote>",
     '<blockquote>foo <a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a>bar</blockquote>'),
    # Otherwise put a page label inside the following tag:
    ("<p>foo.</p><p>[935 F.3d 745]</p><p> Bar</p>",
     '<p>foo.</p><p><a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a>Bar</p>'),
    ("<p>foo</p><p>[935 F.3d 745]</p><blockquote> bar</blockquote>",
     '<p>foo</p><blockquote><a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a>bar</blockquote>'),
    ("<blockquote>foo</blockquote><p>[935 F.3d 745]</p><p>bar</p>",
     '<blockquote>foo</blockquote><p><a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a>bar</p>'),
    # handle "Page 745" (example SE2d/621/621SE2d48_1.xml)
    ("<p>foo.</p><p>Page 745</p><p>Bar</p>",
     '<p>foo.</p><p><a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a>Bar</p>'),
    # data-citation-index is set based on valid_reporters order:
    ("<p>foo</p><p>[123 Mass. 745]</p><p>bar</p>",
     '<p>foo <a id="p745" href="#p745" data-label="745" data-citation-index="2" class="page-label">**745</a>bar</p>'),
    # Page numbers will be skipped inside regular text (too ambiguous), unless valid_reporters matches
    # (example of inline numbers -- SE2d/640/640SE2d71_1.xml)
    ("<p>foo. [999 F.3d 745] Bar</p>", '<p>foo. [999 F.3d 745] Bar</p>'),
    ("<p>foo. Page 745 Bar</p>", '<p>foo. Page 745 Bar</p>'),
    ("<p>foo. [935 F.3d 745] Bar</p>",
     '<p>foo. <a id="p745" href="#p745" data-label="745" data-citation-index="1" class="page-label">*745</a> Bar</p>'),
])
def test_fix_page_numbers(input, expected):
    root = PyQuery('<root>'+input+'</root>')
    cites = [Citation(cite="935 F.3d 1", type="official"), Citation(cite="123 Mass. 1", type="parallel")]
    segment_paragraphs(root, cites)
    output = root('root').html(method='html')
    assert output == expected


@pytest.mark.django_db(databases=['capdb'])
def test_fastcase_ingest(tmp_path, pytestconfig, elasticsearch):
    """
        An elaborate test to make sure that all files in test_data/fastcase continue to import the same way.
        This "zoo" of examples helps make sure that we don't mess up heuristics for previously correct Fastcase cases
        when adding heuristics for new cases.
        This is checked in a few different ways:
         - each xml file gets an html file next to it with our converted
         - each case's metadata is written to data.yml
        To add an additional file, copy the xml file and then run `pytest -k test_fastcase_ingest --recreate_fastcase_files`
    """
    # set up db fixtures, and cases to ingest in a temp dir
    fastcase_dir = Path(settings.BASE_DIR, 'test_data/fastcase')
    copy_tree(str(fastcase_dir), str(tmp_path))
    management.call_command('loaddata', 'capdb/fixtures/jurisdiction.capdb.json.gz', 'capdb/fixtures/reporter.capdb.json.gz', database='capdb')

    # run the ingest
    ingest_fastcase.pack_volumes(tmp_path, recreate=True)
    ingest_fastcase.main(batch='test_batch', base_dir=tmp_path)
    refresh_case_body_cache()
    update_elasticsearch_from_queue()

    # gather metadata for imported cases
    data = {}
    for volume in VolumeMetadata.objects.order_by('reporter__short_name'):
        volume_data = model_to_dict(volume, fields=['reporter', 'volume_number', 'contributing_library', 'notes', 'ingest_status'])
        cases = {}
        for case in volume.case_metadatas.all():
            case_data = model_to_dict(case, fields=[
                'source', 'batch', 'frontend_url', 'first_page', 'last_page', 'first_page_order', 'last_page_order',
                'docket_number', 'docket_numbers', 'decision_date_original', 'name', 'name_abbreviation'])
            case_data['reporter'] = model_to_dict(case.reporter, fields=['short_name'])
            case_data['jurisdiction'] = model_to_dict(case.jurisdiction, fields=['name'])
            case_data['court'] = model_to_dict(case.court, fields=['name', 'name_abbreviation'])
            case_data['court']['jurisdiction'] = model_to_dict(case.court.jurisdiction, fields=['name'])
            case_data['fastcase_import'] = model_to_dict(case.fastcase_import, fields=['path', 'batch'])
            case_data['citations'] = [model_to_dict(c, fields=['type', 'category', 'cite', 'normalized_cite']) for c in case.citations.order_by('cite')]
            case_data['analysis'] = [model_to_dict(c, fields=['key', 'value']) for c in case.analysis.order_by('key')]
            case_data['has_body_cache'] = bool(case.body_cache)
            cases[case.case_id] = case_data
            # check case html for changes
            check_path(pytestconfig, case.body_cache.html,
                       fastcase_dir.joinpath(case.fastcase_import.path).with_suffix('.html'))
        volume_data['cases'] = cases
        data[volume.pk] = volume_data
    data = sort_nested_dict(data)

    # check metadata files for changes
    check_path(pytestconfig, yaml.dump(data), fastcase_dir / 'data.yml')
