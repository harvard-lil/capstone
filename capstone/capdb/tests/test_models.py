import pytest

from django.utils.text import slugify

from capdb.models import CaseMetadata, CaseImage, fetch_relations, Court, EditLog, CaseBodyCache
from capdb.tasks import retrieve_images_from_cases
from test_data.test_fixtures.helpers import xml_equal


### test our model helpers ###


@pytest.mark.django_db
def test_fetch_relations(case, court, django_assert_num_queries):
    case = CaseMetadata.objects.get(pk=case.pk)
    with django_assert_num_queries(select=2):
        fetch_relations(case, select_relations=['volume__reporter', 'jurisdiction'], prefetch_relations=['citations'])
    with django_assert_num_queries():
        fetch_relations(case, select_relations=['volume__reporter', 'jurisdiction'], prefetch_relations=['citations'])
    with django_assert_num_queries():
        assert case.jurisdiction
    with django_assert_num_queries():
        assert case.volume.reporter
    with django_assert_num_queries():
        assert len(list(case.citations.all()))

    # can prefetch_related on sub-relationships
    body_cache = CaseBodyCache.objects.first()
    with django_assert_num_queries(select=2):
        fetch_relations(body_cache, prefetch_relations=['metadata__citations'])
    with django_assert_num_queries():
        assert len(list(body_cache.metadata.citations.all()))

    # can change items and it fetches relations of sub-items
    case = CaseMetadata.objects.get(pk=case.pk)
    court = Court.objects.get(pk=court.pk)
    assert case.court != court
    case.court = court
    with django_assert_num_queries(select=1):
        fetch_relations(case, select_relations=['court__jurisdiction'])
    with django_assert_num_queries():
        assert case.court == court
        assert case.court.jurisdiction


### VolumeMetadata ###

@pytest.mark.django_db
def test_volume_save_slug_update(volume_metadata):
    original_volume_number = volume_metadata.volume_number
    volume_metadata.volume_number = "77777"
    volume_metadata.save(update_volume_number_slug=False)
    volume_metadata.refresh_from_db()

    assert volume_metadata.volume_number != original_volume_number
    assert slugify(volume_metadata.volume_number) != volume_metadata.volume_number_slug

    volume_metadata.volume_number = "88888"
    volume_metadata.save()
    volume_metadata.refresh_from_db()

    assert volume_metadata.volume_number == "88888"
    assert slugify(volume_metadata.volume_number) == volume_metadata.volume_number_slug


@pytest.mark.django_db
def test_volume_unredact(case_factory):
    # set up a redacted case
    case = case_factory(volume__redacted=True, volume__pdf_file='')
    structure = case.structure
    page = structure.pages.first()
    structure.opinions = [
        # redacted paragraph
        {
            'type': 'head',
            'paragraphs': [
                {'class': 'parties', 'block_ids': ['BL_1.1'], 'id': 'b1-1', 'redacted': True}
            ],
        }, {
            'type': 'majority',
            'paragraphs': [
                # redacted content blocks
                {'class': 'p', 'block_ids': ['BL_1.2', 'BL_1.3'], 'id': 'b1-2'},
                # redacted image block
                {'class': 'image', 'block_ids': ['BL_1.4'], 'id': 'b1-3'},
            ],
            # redacted footnote
            'footnotes': [
                {
                    # redacted footnote paragraph
                    'paragraphs': [
                        {'class': 'p', 'block_ids': ['BL_1.5'], 'id': 'b1-4'}
                    ],
                    'label': '1',
                    'id': 'footnote_1_1',
                    'redacted': True,
                }
            ],
        }
    ]
    structure.save()
    page.blocks = [
        {"id": "BL_1.1", "class": "p", "tokens": ["Text 1"]},
        {"id": "BL_1.2", "class": "p", "tokens": ["Text 2"], "redacted": True},
        {"id": "BL_1.3", "class": "p", "tokens": [["redact"], "Text 3", ["/redact"]]},
        {"id": "BL_1.4", "format": "image", "redacted": True, "class": "image", "data": "image data", "rect": [0, 0, 100, 100]},
        {"id": "BL_1.5", "class": "p", "tokens": ["Text 4"]},
    ]
    page.encrypt()
    page.save()

    # verify redacted case contents
    case.sync_case_body_cache()
    case.refresh_from_db()
    assert case.body_cache.text == '\n\n'
    assert 'src="data:image data"' not in case.body_cache.html

    # unredact
    volume = case.volume
    volume.unredact()
    volume.refresh_from_db()
    case.body_cache.refresh_from_db()
    assert volume.redacted is False
    assert case.body_cache.text == 'Text 1\nText 2Text 3\nText 4\n'
    assert 'src="data:image data"' in case.body_cache.html



### BaseXMLModel ###

@pytest.mark.django_db
def test_database_should_not_modify_xml(volume_xml, unaltered_alto_xml):
    # make sure that XMLField.from_db_value is doing its job and putting the correct XML declaration back in:
    volume_xml.orig_xml = unaltered_alto_xml
    volume_xml.save()
    volume_xml.refresh_from_db()
    assert volume_xml.orig_xml == unaltered_alto_xml.decode()
    assert volume_xml.md5 == volume_xml.get_md5()


### CaseMetadata ###

@pytest.mark.django_db
def test_withdraw_case(case_factory):
    withdrawn = case_factory()
    replaced_by = case_factory()
    withdrawn.withdraw(True, replaced_by)
    withdrawn.refresh_from_db()
    assert withdrawn.withdrawn
    assert withdrawn.replaced_by == replaced_by
    assert 'This case was withdrawn and replaced' in withdrawn.body_cache.html
    assert 'This case was withdrawn and replaced' in withdrawn.body_cache.xml

@pytest.mark.django_db
def test_update_frontend_urls(case_factory, django_assert_num_queries):
    case1 = case_factory(citations__cite="123 Test 456", volume__volume_number="123", citations__type="official")
    case2 = case_factory(citations__cite="124 Test 456", volume__volume_number="124", citations__type="official")
    cite2 = case2.citations.first()

    assert case1.frontend_url == "/test/123/456/"
    assert case2.frontend_url == "/test/124/456/"

    cite2.cite = "123 Test 456"
    case2.volume.volume_number = "123"
    case2.volume.save()
    cite2.save()
    with django_assert_num_queries(select=1, update=1):
        CaseMetadata.update_frontend_urls(["124 Test 456", "123 Test 456"], update_elasticsearch=False)
    case1.refresh_from_db()
    case2.refresh_from_db()

    assert case1.frontend_url == "/test/123/456/%s/" % case1.id
    assert case2.frontend_url == "/test/123/456/%s/" % case2.id

    cite2.cite = "124 Test 456"
    cite2.save()
    case2.volume.volume_number = "124"
    case2.volume.save()
    CaseMetadata.update_frontend_urls(["124 Test 456", "123 Test 456"], update_elasticsearch=False)
    case1.refresh_from_db()
    case2.refresh_from_db()

    assert case1.frontend_url == "/test/123/456/"
    assert case2.frontend_url == "/test/124/456/"

@pytest.mark.django_db
def test_sync_case_body_cache(reset_sequences, case):
    # set up case
    structure = case.structure
    page = structure.pages.first()
    structure.opinions = [
        {
            'type': 'head',
            'paragraphs': [{'class': 'parties', 'block_ids': ['BL_1.1'], 'id': 'b1-1'}],
        }, {
            'type': 'majority',
            'paragraphs': [{'class': 'p', 'block_ids': ['BL_1.2', 'BL_1.3'], 'id': 'b1-2'}],
            'footnotes': [
                {
                    'id': 'footnote_1_1',
                    'paragraphs': [{'class': 'p', 'block_ids': ['BL_1.4'], 'id': 'b1-4'}],
                    'label': '1',
                }
            ],
        }
    ]
    structure.save()
    page.blocks = [{"id": "BL_1.%s" % i, "class": "p", "tokens": ["Text %s" % i]} for i in range(1, 5)]
    page.save()

    # verify case contents
    case.sync_case_body_cache()
    assert case.body_cache.text == 'Text 1\nText 2Text 3\nText 4\n'
    assert xml_equal(case.body_cache.html,
        '<section class="casebody" data-case-id="00000000" data-firstpage="4" data-lastpage="8">\n'
        '  <section class="head-matter">\n'
        '    <h4 class="parties" id="b1-1">Text 1</h4>\n'
        '  </section>\n'
        '  <article class="opinion" data-type="majority">\n'
        '    <p id="b1-2">Text 2Text 3</p>\n'
        '    <aside class="footnote" data-label="1" id="footnote_1_1">\n'
        '      <a href="#ref_footnote_1_1">1</a>\n'
        '      <p id="b1-4">Text 4</p>\n'
        '    </aside>\n'
        '  </article>\n'
        '</section>\n')
    assert case.body_cache.json == {
        'attorneys': [],
        'parties': ['Text 1'],
        'judges': [],
        'opinions': [
            {
                'type': 'majority',
                'author': None,
                'text': 'Text 2Text 3\nText 4'
            }],
        'head_matter': 'Text 1',
        'corrections': ''
    }
    assert xml_equal(case.body_cache.xml,
        '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
        '<casebody firstpage="4" lastpage="8" xmlns="http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1">\n'
        '  <parties id="b1-1">Text 1</parties>\n'
        '  <opinion type="majority">\n'
        '    <p id="b1-2">Text 2Text 3</p>\n'
        '    <footnote label="1">\n'
        '      <p id="b1-4">Text 4</p>\n'
        '    </footnote>\n'
        '  </opinion>\n'
        '</casebody>\n')


### EditLog and EditLogTransaction ###

@pytest.mark.django_db
def test_data_edit(volume_metadata):
    with EditLog(description="test").record() as edit:
        volume_metadata.publisher = "foo"
        volume_metadata.save()
    transactions = list(edit.transactions.all())
    assert len(transactions) == 1
    volume_metadata.refresh_from_db()
    assert transactions[0].timestamp == volume_metadata.sys_period.lower


### CaseImage ###

@pytest.mark.django_db
def test_retrieve_and_store_images(case, inline_image_src, django_assert_num_queries):
    assert not CaseImage.objects.exists()

    # index for first time
    case.body_cache.html = "<img src='image/png;base64,%s'>" % inline_image_src
    case.body_cache.save()
    with django_assert_num_queries(select=3, insert=1, update=1):
        retrieve_images_from_cases(case.volume_id)
    assert CaseImage.objects.count() == 1

    # index for second time
    with django_assert_num_queries(select=3, update=2):
        retrieve_images_from_cases(case.volume_id)
    assert CaseImage.objects.count() == 1
