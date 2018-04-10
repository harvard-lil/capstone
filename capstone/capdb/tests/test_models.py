import pytest

from django.utils.encoding import force_bytes

from scripts.helpers import parse_xml, serialize_xml, nsmap
from test_data.test_fixtures.factories import *

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
def test_create_or_update_metadata(ingest_case_xml):
    # fetch current metadata
    case_metadata = ingest_case_xml.metadata

    # change xml
    parsed = parse_xml(ingest_case_xml.orig_xml)
    parsed('case|citation[category="official"]').text('123 Test 456')

    ingest_case_xml.orig_xml = serialize_xml(parsed)
    ingest_case_xml.save()

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
    ingest_case_xml.orig_xml = serialize_xml(parsed)
    ingest_case_xml.save()
    # fetch new metadata
    new_case_metadata = CaseMetadata.objects.get(pk=case_metadata.pk)
    assert new_case_metadata.opinions == {"majority": new_author}

    # strip soft dashes
    ingest_case_xml.orig_xml = ingest_case_xml.orig_xml.replace(new_author, new_author + '\xad')
    ingest_case_xml.save()
    ingest_case_xml.metadata.refresh_from_db()
    assert ingest_case_xml.metadata.opinions['majority'] == new_author

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
    short_alto_identifier = 'alto_00009_0'
    short_case_identifier = 'casemets_0001'
    initial_casemets_alto_md5 = parsed_case_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_volume_alto_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_alto_identifier)).attr["CHECKSUM"]
    initial_volume_case_md5 = parsed_volume_xml('mets|file[ID="{}"]'.format(short_case_identifier)).attr["CHECKSUM"]
    assert initial_casemets_alto_md5 == alto.md5
    assert initial_volume_case_md5 == ingest_case_xml.md5

    # change a word in the case XML
    updated_text = parsed_case_xml('casebody|p[id="b17-6"]').text().replace('argument', '4rgUm3nt')
    parsed_case_xml('casebody|p[id="b17-6"]').text(updated_text)
    ingest_case_xml.orig_xml = serialize_xml(parsed_case_xml)
    with django_assert_num_queries(select=5, update=4):
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
    assert new_volume_case_md5 != initial_volume_case_md5
    assert new_volume_alto_md5 != initial_volume_alto_md5
    assert new_casemets_alto_md5 == alto.md5
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


# PageXML update

@pytest.mark.django_db
def test_checksums_alto_update(ingest_case_xml):
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
    assert new_volume_alto_md5 != initial_volume_alto_md5
    assert new_casemets_alto_md5 == alto.md5
    assert new_volume_alto_md5 == alto.md5
    assert new_casemets_alto_size != initial_casemets_alto_size
    assert new_volume_alto_size != initial_volume_alto_size
    assert new_casemets_alto_size == str(len(force_bytes(alto.orig_xml)))
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
