from textwrap import dedent

import pytest
import re

from django.utils.text import slugify

from capdb.models import CaseMetadata, CaseImage, fetch_relations, Court, EditLog, CaseBodyCache, VolumeMetadata
from capdb.tasks import retrieve_images_from_cases, update_elasticsearch_from_queue
from test_data.test_fixtures.helpers import xml_equal, set_case_text, html_equal
from capapi.documents import CaseDocument


### test our model helpers ###

@pytest.mark.django_db(databases=['capdb'])
def test_sync_case_body_cache(reset_sequences, case, elasticsearch, case_factory):
    set_case_text(case, "Foo v. Bar, 1 U.S. 1. ", "Case text 2")
    target_case = case_factory(citations__cite="1 U.S. 1")
    # verify case contents
    case.sync_case_body_cache()
    assert case.body_cache.text == 'Case text 0\nFoo v. Bar, 1 U.S. 1. Case text 2\nCase text 3\n'
    assert xml_equal(case.body_cache.html,
        '<section class="casebody" data-case-id="00000000" data-firstpage="4" data-lastpage="8">\n'
        '  <section class="head-matter">\n'
        '    <h4 class="parties" id="b81-4">Case text 0</h4>\n'
        '  </section>\n'
        '  <article class="opinion" data-type="majority">\n'
        f'    <p id="b83-6">Foo v. Bar, <a href="http://cite.case.test:8000/us/1/1/" class="citation" data-index="0" data-case-ids="{target_case.id}">1 U.S. 1</a>. Case text 2</p>\n'
        '    <aside class="footnote" data-label="1" id="footnote_1_1">\n'
        '      <a href="#ref_footnote_1_1">1</a>\n'
        '      <p id="b83-11">Case text 3</p>\n'
        '    </aside>\n'
        '  </article>\n'
        '</section>\n')
    assert case.body_cache.json == {
        'attorneys': [],
        'parties': ['Case text 0'],
        'judges': [],
        'opinions': [
            {
                'type': 'majority',
                'author': None,
                'text': 'Foo v. Bar, 1 U.S. 1. Case text 2\nCase text 3'
            }],
        'head_matter': 'Case text 0',
        'corrections': ''
    }
    assert xml_equal(case.body_cache.xml,
        '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
        '<casebody firstpage="4" lastpage="8" xmlns="http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1">\n'
        '  <parties id="b81-4">Case text 0</parties>\n'
        '  <opinion type="majority">\n'
        f'    <p id="b83-6">Foo v. Bar, <extracted-citation url="http://cite.case.test:8000/us/1/1/" index="0" case-ids="{target_case.id}">1 U.S. 1</extracted-citation>. Case text 2</p>\n'
        '    <footnote label="1">\n'
        '      <p id="b83-11">Case text 3</p>\n'
        '    </footnote>\n'
        '  </opinion>\n'
        '</casebody>\n')