import pytest

from capdb.models import CaseMetadata
from scripts.helpers import parse_xml, serialize_xml


### CaseMetadata ###

@pytest.mark.django_db
def test_create_or_update_metadata(case_xml):
    # fetch current metadata
    case_metadata = case_xml.metadata

    # change xml
    parsed = parse_xml(case_xml.orig_xml)
    parsed('case|citation[category="official"]').text('123 Test 456')
    case_xml.orig_xml = serialize_xml(parsed)
    case_xml.save()
    case_xml.create_or_update_metadata()

    # fetch new metadata
    new_case_metadata = CaseMetadata.objects.get(pk=case_metadata.pk)
    new_citations = list(new_case_metadata.citations.all())

    # case_metadata should have been updated, not duplicated
    assert new_case_metadata.pk == case_metadata.pk
    assert new_case_metadata.slug == '123-test-456'

    # citations should have been replaced
    assert len(new_citations) == 1
    assert new_citations[0].cite == '123 Test 456'

    # testing calling without updating metadata
    old_case_metadata = new_case_metadata
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    case_parent_tag = parsed_case_xml('case|case')
    case_parent_tag.remove('case|name')
    case_parent_tag.remove('case|citation')
    case_xml.orig_xml = serialize_xml(parsed_case_xml)
    case_xml.save()
    case_xml.refresh_from_db()
    case_xml.create_or_update_metadata(update_existing=False)
    new_case_metadata = CaseMetadata.objects.get(pk=case_metadata.pk)
    assert new_case_metadata == old_case_metadata


@pytest.mark.django_db
def test_casebody_modify_word(case_xml):
    # change a word in the case XML
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    updated_text = parsed_case_xml('casebody|p[id="b17-6"]').text().replace('argument', '4rgUm3nt')
    parsed_case_xml('casebody|p[id="b17-6"]').text(updated_text)
    case_xml.orig_xml = serialize_xml(parsed_case_xml)
    case_xml.save()
    case_xml.refresh_from_db()
    parsed_case_xml = parse_xml(case_xml.orig_xml)
    assert '4rgUm3nt' in parsed_case_xml('casebody|p[id="b17-6"]').text() 
    # make sure the change shows up in the ALTO
    alto = case_xml.pages.get(barcode="32044057892259_00009_0")
    parsed_alto = parse_xml(alto.orig_xml)
    element = parsed_alto('alto|String[ID="ST_17.7.1.3"]')
    assert element.attr["CONTENT"] == '4rgUm3nt'

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


