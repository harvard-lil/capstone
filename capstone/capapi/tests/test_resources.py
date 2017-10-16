import pytest
import os
import zipfile

from django.conf import settings

from capapi import resources
from capdb.models import CaseXML
from test_data.factories import *


@pytest.mark.django_db
def test_write_and_zip():
    """
    test that we're writing and zipping the case_xmls correctly
    """
    case_one = setup_case()

    # insert unique str in dummy xml to be sure we're writing the correct one
    case_xml = CaseXML.objects.get(case_id=case_one.case_id)
    case_xml.orig_xml = case_xml.orig_xml.split("</mets>")[0] + "<case_id>%s</case_id></mets>" % case_xml.case_id
    case_xml.save()

    zipped_dirname = resources.write_and_zip([case_one])
    assert os.path.exists(zipped_dirname)
    assert case_one.slug in zipped_dirname
    assert settings.API_ZIPFILE_DIR in zipped_dirname

    # unzip everything, check if contents are available
    zipfile_handler = zipfile.ZipFile(zipped_dirname, 'r')
    zipfile_handler.extractall()
    zipfile_handler.close()

    unzipped_dirname = zipped_dirname.replace('.zip', '/')

    with open(unzipped_dirname + case_one.slug + ".xml", "r") as f:
        file_contents = f.read()

    assert case_xml.orig_xml == file_contents
    assert "<case_id>%s" % case_xml.case_id in file_contents


