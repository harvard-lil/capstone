import re
import pytest

from django.utils.encoding import force_bytes
from django.utils.text import slugify

from capdb.models import VolumeMetadata, CaseMetadata, CaseImage, CaseBodyCache, CaseXML, fetch_relations, Jurisdiction, \
    Reporter, Court, EditLog
from capdb.tasks import retrieve_images_from_cases
from scripts.helpers import nsmap, parse_xml, serialize_xml


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


### VolumeXML ###

@pytest.mark.django_db
def test_volumexml_update_metadata(volume_xml, ingest_volume_xml):
    # metadata is extracted during initial save:
    assert int(volume_xml.metadata.xml_start_year) == 1877
    assert int(volume_xml.metadata.xml_end_year) == 1887
    assert int(volume_xml.metadata.xml_publication_year) == 1888
    assert int(volume_xml.metadata.xml_volume_number) == 23
    assert volume_xml.metadata.xml_publisher == "Callaghan & Company"
    assert volume_xml.metadata.xml_publication_city == "Chicago, IL"
    assert volume_xml.metadata.xml_reporter_short_name == "Ill. App."
    assert volume_xml.metadata.xml_reporter_full_name == "Illinois Appellate Court Reports"



    # metadata is extracted during update:
    volume_xml.orig_xml = volume_xml.orig_xml.replace('1888', '1999')
    volume_xml.save()
    volume_xml.metadata.refresh_from_db()
    assert volume_xml.metadata.xml_publication_year == 1999

    # with new style barcode/volume
    new_style_vol = VolumeMetadata.objects.get(pk="WnApp_199")
    new_style_vol.xml_publication_year = 1200
    new_style_vol.save()
    new_style_vol.refresh_from_db()
    assert new_style_vol.xml_publication_year == 1200

    new_style_vol.volume_xml.orig_xml = new_style_vol.volume_xml.orig_xml.replace("2018", "3018")
    new_style_vol.volume_xml.save()
    new_style_vol.refresh_from_db()
    assert new_style_vol.xml_publication_year == 3018



### CaseMetadata ###

@pytest.mark.django_db
def test_create_or_update_metadata(ingest_case_xml):
    cases = [ingest_case_xml, CaseMetadata.objects.get(case_id="WnApp_199_0036").case_xml]
    for case in cases:
        # fetch current metadata
        case_metadata = case.metadata
        # change xml
        parsed = parse_xml(case.orig_xml)
        parsed('case|citation[category="official"]').text('123 Test 456')

        case.orig_xml = serialize_xml(parsed)
        case.save()

        # fetch new metadata
        new_case_metadata = CaseMetadata.objects.get(pk=case_metadata.pk)
        new_citations = list(new_case_metadata.citations.all())

        # case_metadata should have been updated, not duplicated
        assert new_case_metadata.pk == case_metadata.pk

        # citations should have been replaced
        assert len(new_citations) == 1
        assert new_citations[0].cite == '123 Test 456'

        # test update author
        new_author = "Lacey, John"
        parsed('casebody|author').text(new_author)
        case.orig_xml = serialize_xml(parsed)
        case.save()
        # fetch new metadata
        new_case_metadata = CaseMetadata.objects.get(pk=case_metadata.pk)
        assert new_case_metadata.opinions == [{"type": "majority", "author": new_author}]

        # strip soft dashes
        case.orig_xml = case.orig_xml.replace(new_author, new_author + '\xad')
        case.save()
        case.metadata.refresh_from_db()
        assert case.metadata.opinions[0]['author'] == new_author

@pytest.mark.django_db
def test_denormalized_fields(case):
    jurisdiction = case.jurisdiction
    jurisdiction.whitelisted = True
    jurisdiction.save()

    # if source is set to none, destination fields should be nulled out
    case.jurisdiction = None
    case.save()
    case.refresh_from_db()
    assert case.jurisdiction_name is None
    assert case.jurisdiction_whitelisted is None

    # if source foreign key is changed, destination fields should be updated
    case.jurisdiction = jurisdiction
    case.save()
    case.refresh_from_db()
    assert case.jurisdiction_name == jurisdiction.name
    assert case.jurisdiction_whitelisted == jurisdiction.whitelisted

    # if source fields are changed, destination fields should be updated
    jurisdiction.whitelisted = False
    jurisdiction.name = 'foo'
    jurisdiction.save()
    case.refresh_from_db()
    assert case.jurisdiction_name == jurisdiction.name
    assert case.jurisdiction_whitelisted == jurisdiction.whitelisted
    
    court = case.court
    case.court = None
    case.save()
    case.refresh_from_db()
    assert case.court_name is None
    assert case.court_name_abbreviation is None

    # if source foreign key is changed, destination fields should be updated
    case.court = court
    case.save()
    case.refresh_from_db()
    assert case.court_name == court.name
    assert case.court_slug == court.slug
    court.name = 'foo'
    court.save()
    case.refresh_from_db()
    assert case.court_name == court.name

@pytest.mark.django_db
def test_withdraw_case(case_factory):
    withdrawn = case_factory()
    replaced_by = case_factory()
    withdrawn.withdraw(True, replaced_by)
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

### Case Full Text Search ###
@pytest.mark.django_db
def test_fts_create_index(ingest_case_xml):
    case_text = ingest_case_xml.metadata.case_text

    assert '4rgum3nt' not in case_text.tsv
    # change a word in the case XML
    ingest_case_xml.orig_xml = ingest_case_xml.orig_xml.replace('argument', '4rgum3nt')
    ingest_case_xml.save()

    # make sure the change was saved in the case_xml
    case_text.refresh_from_db()
    assert '4rgum3nt' in case_text.tsv

### CaseXML ###

@pytest.mark.django_db
def test_related_names(case_xml):
    volxml = case_xml.volume
    case = case_xml.metadata

    assert case_xml in volxml.case_xmls.all()

    jur = Jurisdiction.objects.get(pk=case.jurisdiction.pk)
    rep = Reporter.objects.get(pk=case.reporter.pk)
    vol = VolumeMetadata.objects.get(pk=case.volume.pk)
    court = Court.objects.get(pk=case.court.pk)

    assert case in jur.case_metadatas.all()
    assert case in rep.case_metadatas.all()
    assert case in court.case_metadatas.all()
    assert case in vol.case_metadatas.all()


# CaseXML update

@pytest.mark.django_db
def test_checksums_update_casebody_modify_word(ingest_case_xml, django_assert_num_queries):

    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    alto = ingest_case_xml.pages.get(barcode="32044057892259_00009_0")

    # get ALTO
    short_alto_identifier = alto.short_id
    short_case_identifier = ingest_case_xml.short_id
    initial_casemets_alto_md5 = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_volume_case_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_case_identifier)).attr["CHECKSUM"]
    assert initial_casemets_alto_md5 == alto.md5
    assert initial_volume_case_md5 == ingest_case_xml.md5

    # change a word in the case XML
    updated_text = parsed_case_xml('casebody|p[id="b17-6"]').text().replace('argument', '4rgUm3nt')
    parsed_case_xml('casebody|p[id="b17-6"]').text(updated_text)
    ingest_case_xml.orig_xml = serialize_xml(parsed_case_xml)
    with django_assert_num_queries(select=6, update=5):
        ingest_case_xml.save()

    # make sure the change was saved in the case_xml
    ingest_case_xml.refresh_from_db()
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    assert '4rgUm3nt' in parsed_case_xml('casebody|p[id="b17-6"]').text()

    # make sure the change shows up in the ALTO
    alto.refresh_from_db()
    assert '4rgUm3nt' in parse_xml(alto.orig_xml)('alto|String[ID="ST_17.7.1.3"]').attr["CONTENT"]

    #make sure the md5s got updated
    new_casemets_alto_md5 = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_volume_case_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_case_identifier)).attr["CHECKSUM"]

    # make sure the md5 has changed, and that it's the correct current md5
    assert new_casemets_alto_md5 != initial_casemets_alto_md5
    assert new_casemets_alto_md5 == alto.md5

    # volume xml should still have old md5
    assert new_volume_alto_md5 == initial_volume_alto_md5
    assert new_volume_case_md5 == initial_volume_case_md5

    # now update volume checksums
    assert ingest_case_xml.volume.metadata.xml_checksums_need_update
    ingest_case_xml.volume.update_checksums()
    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    new_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_volume_case_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_case_identifier)).attr["CHECKSUM"]

    # volume xml should have new md5
    assert new_volume_case_md5 != initial_volume_case_md5
    assert new_volume_alto_md5 != initial_volume_alto_md5
    assert new_volume_alto_md5 == alto.md5
    assert new_volume_case_md5 == ingest_case_xml.md5


# CaseXML update

@pytest.mark.django_db
def test_save_related_update_disabled(ingest_case_xml):

    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    alto = ingest_case_xml.pages.get(barcode="32044057892259_00009_0")

    # get ALTO

    # change a word in the case XML
    updated_text = parsed_case_xml('casebody|p[id="b17-6"]').text().replace('argument', '4rgUm3nt')
    parsed_case_xml('casebody|p[id="b17-6"]').text(updated_text)
    ingest_case_xml.orig_xml = serialize_xml(parsed_case_xml)
    ingest_case_xml.save(update_related=False)


    # make sure the change was saved in the case_xml
    ingest_case_xml.refresh_from_db()
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    assert '4rgUm3nt' in parsed_case_xml('casebody|p[id="b17-6"]').text()

    # make sure the change shows up in the ALTO
    alto.refresh_from_db()
    assert '4rgUm3nt' not in parse_xml(alto.orig_xml)('alto|String[ID="ST_17.7.1.3"]').attr["CONTENT"]


@pytest.mark.django_db
def test_case_alter_structure(case_xml):
    # make non-casebody structural changes

    #make sure we've got our decision date
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    case_parent_tag = parsed_case_xml('case|case')
    assert case_parent_tag('case|decisiondate') is not []


    #remove it and make sure it sticks
    case_parent_tag.remove('case|decisiondate')
    case_xml.orig_xml = serialize_xml(parsed_case_xml)
    case_xml.save()

    # make sure it saves
    case_xml.refresh_from_db()
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    case_parent_tag = parsed_case_xml('case|case')
    assert case_parent_tag('case|decisiondate') == []


    #try adding a new element and make sure it saves
    assert case_parent_tag('case|test') == []
    case_parent_tag.append('<test>Frankly, this element is hot garbage.</test>')
    case_xml.orig_xml = serialize_xml(parsed_case_xml)
    case_xml.save()
    case_xml.refresh_from_db()
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    case_parent_tag = parsed_case_xml('case|case')
    assert case_parent_tag('case|test') != []


@pytest.mark.django_db
def test_case_rename_tag(ingest_case_xml):
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    new_tag_name = "judges"
    # make non-casebody structural changes
    parties_element = parsed_case_xml('casebody|parties')[0]
    parties_element.tag = "{{{}}}{}".format(nsmap['casebody'], new_tag_name)
    ingest_case_xml.orig_xml = serialize_xml(parsed_case_xml)
    ingest_case_xml.save()
    ingest_case_xml.refresh_from_db()
    
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    assert len(parsed_case_xml('casebody|judges')) == 1

    alto = ingest_case_xml.pages.get(barcode="32044057892259_00008_0")
    parsed_alto_xml = parse_xml(alto.orig_xml)
    assert parsed_alto_xml('alto|StructureTag[ID="b15-4"]').attr["LABEL"] == new_tag_name



@pytest.mark.django_db
def test_casebody_delete_element_raise(case_xml):
    # make a non-casebody structural change
    with pytest.raises(Exception, match='No current support for removing casebody elements'):
        parsed_case_xml = parse_xml(case_xml.orig_xml)
        case_parent_tag = parsed_case_xml('casebody|casebody')
        case_parent_tag.remove('casebody|parties')
        case_xml.orig_xml = serialize_xml(parsed_case_xml)
        case_xml.save()

@pytest.mark.django_db
def test_casebody_add_element_raise(case_xml):
    # make a non-casebody structural change
    with pytest.raises(Exception, match='No current support for adding casebody elements'):
        parsed_case_xml = parse_xml(case_xml.orig_xml)
        case_parent_tag = parsed_case_xml('casebody|casebody')
        case_parent_tag.append('<test>Frankly, this element is hot garbage.</test>')
        case_xml.orig_xml = serialize_xml(parsed_case_xml)
        case_xml.save()

@pytest.mark.django_db
def test_casebody_delete_word_raise(case_xml):
    # change a word in the case XML
    with pytest.raises(Exception, match='No current support for adding or removing case text'):
        parsed_case_xml = parse_xml(case_xml.orig_xml)
        parsed_case_xml('casebody|p[id="b17-6"]').text("The in favor of the appellee rests wholly on the assumption that the judgment in the garnishee proceedings should be rendered in favor of the judgment debtor for the use of the judgment creditor, against the garnished party, for the whole amount due, and in case of failure to so render judgment for such amount and for a less amount than due, the balance over and above the amount of the judgment so rendered would be barred on the grounds of former recovery.")
        case_xml.orig_xml = serialize_xml(parsed_case_xml)
        case_xml.save()

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


# PageXML update

@pytest.mark.django_db
def test_checksums_alto_update(ingest_case_xml):
    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    alto = ingest_case_xml.pages.get(barcode="32044057892259_00009_0")
    parsed_alto_xml = parse_xml(alto.orig_xml)


    # get initial values
    short_alto_identifier = alto.short_id
    initial_casemets_alto_md5 = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_casemets_alto_size = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]
    initial_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_volume_alto_size = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]

    # change a value in the ALTO file
    parsed_alto_xml('alto|TextStyle[ID="Style_1"]').attr["FONTFAMILY"] = 'Juggalo Sans'
    alto.orig_xml = serialize_xml(parsed_alto_xml)
    alto.save()

    # make sure the change was saved in the file
    alto.refresh_from_db()
    parsed_alto_xml = parse_xml(alto.orig_xml)
    assert parsed_alto_xml('alto|TextStyle[ID="Style_1"]').attr["FONTFAMILY"] == 'Juggalo Sans'


    ingest_case_xml.refresh_from_db()
    ingest_case_xml.volume.refresh_from_db()
    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)

    # make sure the md5s got updated
    new_casemets_alto_md5 = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_casemets_alto_size = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]
    new_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_volume_alto_size = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]

    # make sure the md5 and size have changed, and that it's the correct current md5
    assert new_casemets_alto_md5 != initial_casemets_alto_md5
    assert new_casemets_alto_md5 == alto.md5
    assert new_casemets_alto_size != initial_casemets_alto_size
    assert new_casemets_alto_size == str(len(force_bytes(alto.orig_xml)))

    # volume xml should still have old md5
    assert new_volume_alto_md5 == initial_volume_alto_md5
    assert new_volume_alto_size == initial_volume_alto_size

    # now update volume checksums
    assert ingest_case_xml.volume.metadata.xml_checksums_need_update
    ingest_case_xml.volume.update_checksums()
    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    new_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_volume_alto_size = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]

    # volume xml should now have new md5
    assert new_volume_alto_md5 != initial_volume_alto_md5
    assert new_volume_alto_md5 == alto.md5
    assert new_volume_alto_size != initial_volume_alto_size
    assert new_volume_alto_size == str(len(force_bytes(alto.orig_xml)))


# PageXML update

@pytest.mark.django_db
def test_alto_update_disable_related(ingest_case_xml):
    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)
    alto = ingest_case_xml.pages.get(barcode="32044057892259_00009_0")
    parsed_alto_xml = parse_xml(alto.orig_xml)


    # get initial values
    short_alto_identifier = 'alto_00009_0'
    initial_casemets_alto_md5 = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_casemets_alto_size = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]
    initial_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_volume_alto_size = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]

    # change a value in the ALTO file
    parsed_alto_xml('alto|TextStyle[ID="Style_1"]').attr["FONTFAMILY"] = 'Juggalo Sans'
    alto.orig_xml = serialize_xml(parsed_alto_xml)
    alto.save(save_case=False, save_volume=False)

    # make sure the change was saved in the file
    alto.refresh_from_db()
    parsed_alto_xml = parse_xml(alto.orig_xml)
    assert parsed_alto_xml('alto|TextStyle[ID="Style_1"]').attr["FONTFAMILY"] == 'Juggalo Sans'


    ingest_case_xml.refresh_from_db()
    ingest_case_xml.volume.refresh_from_db()
    parsed_volume_xml = parse_xml(ingest_case_xml.volume.orig_xml)
    parsed_case_xml = parse_xml(ingest_case_xml.orig_xml)

    # make sure the md5s got updated
    new_casemets_alto_md5 = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_casemets_alto_size = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]
    new_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    new_volume_alto_size = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["SIZE"]

    # make sure the md5 and size have changed, and that it's the correct current md5
    assert new_casemets_alto_md5 == initial_casemets_alto_md5
    assert new_volume_alto_md5 == initial_volume_alto_md5
    assert new_casemets_alto_md5 != alto.md5
    assert new_volume_alto_md5 != alto.md5
    assert new_casemets_alto_size == initial_casemets_alto_size
    assert new_volume_alto_size == initial_volume_alto_size
    assert new_casemets_alto_size != str(len(force_bytes(alto.orig_xml)))
    assert new_volume_alto_size != str(len(force_bytes(alto.orig_xml)))

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

