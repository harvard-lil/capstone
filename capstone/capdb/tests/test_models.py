import re
import pytest

from django.utils.text import slugify

from capdb.models import CaseMetadata, CaseImage, CaseBodyCache, CaseXML, fetch_relations, Court, EditLog
from capdb.tasks import retrieve_images_from_cases
from scripts.helpers import parse_xml


### helpers ###


@pytest.mark.django_db
def test_fetch_relations(case, court, django_assert_num_queries):
    case = CaseMetadata.objects.get(pk=case.pk)
    with django_assert_num_queries(select=2):
        fetch_relations(case, select_relations=['volume__volume_xml', 'jurisdiction'], prefetch_relations=['citations'])
    with django_assert_num_queries():
        fetch_relations(case, select_relations=['volume__volume_xml', 'jurisdiction'], prefetch_relations=['citations'])
    with django_assert_num_queries():
        assert case.jurisdiction
    with django_assert_num_queries():
        assert case.volume.volume_xml
    with django_assert_num_queries():
        assert len(list(case.citations.all()))

    # can prefetch_related on sub-relationships
    case_xml = CaseXML.objects.get(pk=case.case_xml.pk)
    with django_assert_num_queries(select=2):
        fetch_relations(case_xml, prefetch_relations=['metadata__citations'])
    with django_assert_num_queries():
        assert len(list(case_xml.metadata.citations.all()))

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

### CaseXML ###

@pytest.mark.django_db
def test_reorder_head_matter(case_xml):
    # To set up test, empty out <casebody> and <div TYPE="blocks"> and replace with new XML.
    # Do this at a string level to avoid trickiness with namespaces.
    parsed = case_xml.get_parsed_xml()
    parsed('casebody|casebody').text("REPLACE_CASEBODY")
    parsed('mets|div[TYPE="blocks"]').text("REPLACE_BLOCKS")
    xml = str(parsed)

    # elements to be reordered
    xml = xml.replace("REPLACE_CASEBODY", """
        <parties id="a">foo</parties>
        <empty id="empty1"> </empty>
        <headnotes id="b">foo</headnotes>
        <headnotes id="c1">foo</headnotes>
        <headnotes id="c2">foo</headnotes>
        <headnotes id="c3">foo</headnotes>
        <opinion type="majority">
            <empty id="empty2"> </empty>
            <p id="d">foo</p>
            <footnote label="†">
                <p id="e">foo</p>
            </footnote>
        </opinion>
        <opinion type="dissent">
            <p id="f">foo</p>
        </opinion>
    """)

    # specify new element order
    pairs = [('b', 'BL_9.9'), ('a', 'BL_9.10'), ('d', 'BL_9.11'), ('c1', 'BL_9.12'), ('e', 'BL_10.9'), ('c2', 'BL_10.10'), ('f', 'BL_10.11'), ('c3', 'BL_10.12'), ('empty1', None), ('empty2', None)]
    xml = xml.replace("REPLACE_BLOCKS", "".join("""
        <div TYPE="element">
            <fptr><area BEGIN="%s" BETYPE="IDREF" FILEID="casebody_0001"/></fptr>
            <fptr><seq>%s</seq></fptr>
        </div>""" % (
            case_id,
            ('<area BEGIN="%s" BETYPE="IDREF" FILEID="alto_00009_0"/>' % alto_id) if alto_id else ''
        ) for case_id, alto_id in pairs))

    # reorder xml
    parsed = parse_xml(xml)
    case_xml.reorder_head_matter(parsed)

    # strip <casebody> tag and whitespace from result, and verify order
    result = str(parsed('casebody|casebody'))
    result = re.sub(r'\s*\n\s*', '', re.sub(r'</?casebody.*?>', '', result), flags=re.S)
    assert result == re.sub(r'\s*\n\s*', '', """
        <headnotes id="b">foo</headnotes>
        <parties id="a">foo</parties>
        <empty id="empty1"> </empty>
        <opinion type="majority">
            <empty id="empty2"> </empty>
            <p id="d">foo</p>
            <headnotes id="c1">foo</headnotes>
            <headnotes id="c2">foo</headnotes>
            <footnote label="†">
                <p id="e">foo</p>
            </footnote>
        </opinion>
        <opinion type="dissent">
            <p id="f">foo</p>
            <headnotes id="c3">foo</headnotes>
        </opinion>
    """, flags=re.S)

# EditLog and EditLogTransaction

@pytest.mark.django_db
def test_data_edit(volume_metadata):
    with EditLog(description="test").record() as edit:
        volume_metadata.publisher = "foo"
        volume_metadata.save()
    transactions = list(edit.transactions.all())
    assert len(transactions) == 1
    volume_metadata.refresh_from_db()
    assert transactions[0].timestamp == volume_metadata.sys_period.lower


@pytest.mark.django_db
def test_retrieve_and_store_images(case, inline_image_src, django_assert_num_queries):
    caseimages = CaseImage.objects.all()
    assert len(caseimages) == 0

    # index for first time
    params = {"html": "<img src='image/png;base64,%s'>" % inline_image_src}
    CaseBodyCache(metadata=case, **params).save()
    with django_assert_num_queries(select=3, insert=1, update=1):
        retrieve_images_from_cases(case.volume_id)
    assert CaseImage.objects.count() == 1

    # index for second time
    with django_assert_num_queries(select=3, update=2):
        retrieve_images_from_cases(case.volume_id)
    assert CaseImage.objects.count() == 1


@pytest.mark.django_db
def test_volume_save_slug_update(case):
    original_volume_number = case.volume.volume_number
    case.volume.volume_number = "77777"
    case.volume.save(update_volume_number_slug=False)
    case.volume.refresh_from_db()

    assert case.volume.volume_number != original_volume_number
    assert slugify(case.volume.volume_number) != case.volume.volume_number_slug

    case.volume.volume_number = "88888"
    case.volume.save()
    case.volume.refresh_from_db()

    assert case.volume.volume_number == "88888"
    assert slugify(case.volume.volume_number) == case.volume.volume_number_slug

