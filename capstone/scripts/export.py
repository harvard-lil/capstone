import hashlib
import zipfile
from datetime import datetime
from pathlib import Path

from django.utils.text import slugify

from capdb.models import Jurisdiction, CaseMetadata, Reporter


def bag_jurisdiction(name, zip_directory=".", zip_filename=None):
    """
        Write a BagIt package of all case XML files in a given jurisdiction.
    """
    jurisdiction = Jurisdiction.objects.get(name=name)
    zip_filename = zip_filename or jurisdiction.slug
    cases = CaseMetadata.objects.filter(jurisdiction=jurisdiction)
    return bag_cases(cases, jurisdiction.name_long, zip_directory, zip_filename)

def bag_reporter(name, zip_directory=".", zip_filename=None):
    """
        Write a BagIt package of all case XML files for a given reporter.
    """
    reporter = Reporter.objects.get(full_name=name)
    zip_filename = zip_filename or slugify(name)
    cases = CaseMetadata.objects.filter(reporter=reporter)
    return bag_cases(cases, name, zip_directory, zip_filename)

def bag_cases(cases, description, zip_directory=".", zip_filename=None):
    """
        Write a BagIt package of all case XML files in a given query.
        See http://gwdev-justinlittman.wrlc.org/bagit.html
    """

    # set up paths
    zip_path = Path(str(zip_directory), str(zip_filename)+"").with_suffix('.zip')
    internal_path = Path(zip_path.stem)

    # set up bagit metadata files
    payload = []
    bagit = "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n"
    baginfo = (
        "Source-Organization: Harvard Law School Library Innovation Lab\n"
        "Organization-Address: 1545 Massachusetts Avenue, Cambridge, MA 02138\n"
        "Contact-Name: Library Innovation Lab\n"
        "Contact-Email: lil@law.harvard.edu\n"
        "External-Description: Case XML for %s\n"
        "Bagging-Date: %s\n"
    ) % (description, datetime.now().strftime("%Y-%m-%d"))

    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as archive:

        # write cases
        for case in cases.select_related('volume', 'reporter'):
            reporter = case.reporter.short_name
            volume = case.volume.volume_number
            filename = case.case_id + '.xml'
            orig_xml = case.case_xml.orig_xml
            sha512 = hashlib.sha512(orig_xml.encode()).hexdigest()
            path = Path("data", reporter, volume, filename)
            archive.writestr(str(internal_path / path), orig_xml)
            payload.append("%s %s" % (sha512, path))

        # write bagit metadata files
        archive.writestr(str(internal_path / "bagit.txt"), bagit)
        archive.writestr(str(internal_path / "bag-info.txt"), baginfo)
        archive.writestr(str(internal_path / "manifest-sha512.txt"), "\n".join(payload))

    return str(zip_path)
