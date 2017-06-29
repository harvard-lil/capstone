import pytest


@pytest.mark.django_db
def test_volume_metadata(volume_xml):
    assert volume_xml.volume_metadata.hollis_number == "005457617"
    assert volume_xml.volume_metadata.rare == False  # boolean conversion

@pytest.mark.django_db
def test_tracking_tool_relationship(volume_xml):
    assert volume_xml.volume_metadata.reporter.full_name == "Illinois Appellate Court Reports"

@pytest.mark.django_db
def test_volume_xml(volume_xml):
    assert '<reporter abbreviation="Ill. App." volnumber="23">Illinois Appellate Court Reports</reporter>' in volume_xml.orig_xml

@pytest.mark.django_db
def test_case_and_page_xml(volume_xml):
    assert volume_xml.case_xmls.count() == 1
    assert volume_xml.page_xmls.count() == 6
    case_xml = volume_xml.case_xmls.first()
    assert '<name abbreviation="Home Insurance Co. of New York v. Kirk">' in case_xml.orig_xml
    assert case_xml.pages.count() == 6
