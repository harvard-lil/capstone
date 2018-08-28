import json
import lzma
import tempfile
import zipfile
from collections import namedtuple
from pathlib import Path
from tempfile import SpooledTemporaryFile

from django.core.files import File
from django.utils import timezone

from capapi.serializers import BulkCaseSerializer
from capapi.views.api_views import CaseViewSet
from capdb.models import Jurisdiction, Reporter, CaseExport
from scripts.helpers import HashingFile


def export_cases_by_jurisdiction(name):
    """
        Write a .jsonl.gz file with all cases for jurisdiction.
    """
    jurisdiction = Jurisdiction.objects.get(name=name)
    cases = CaseViewSet.queryset.filter(jurisdiction=jurisdiction)
    out_path = "{}-{:%Y%m%d}".format(jurisdiction.name_long, timezone.now())
    export_queryset(cases, out_path, jurisdiction, public=jurisdiction.whitelisted)

def export_cases_by_reporter(name):
    """
        Write a .jsonl.gz file with all cases for reporter.
    """
    reporter = Reporter.objects.get(full_name=name)
    cases = CaseViewSet.queryset.filter(reporter=reporter)
    out_path = "{}-{:%Y%m%d}".format(reporter.full_name, timezone.now())
    export_queryset(cases, out_path, reporter, public=False)

def try_to_close(file_handle):
    """
        Cleanup helper used by exception handler. Try calling .close() on file_handle.
        If this fails, presumably file_handle was never opened so no cleanup necessary.
    """
    if file_handle:
        try:
            file_handle.close()
        except Exception:
            pass

def export_queryset(queryset, dir_name, filter_item, public=False):
    """
        Export cases in queryset to dir_name.zip.
        filter_item is the Jurisdiction or Reporter used to select the cases.
        public controls whether export is downloadable by non-researchers.
    """
    formats = {'xml': {}, 'text': {}}

    try:
        # set up vars for each format
        for format_name, vars in formats.items():

            # set up bagit metadata files
            vars['payload'] = []
            vars['bagit'] = "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n"
            vars['baginfo'] = (
                "Source-Organization: Harvard Law School Library Innovation Lab\n"
                "Organization-Address: 1545 Massachusetts Avenue, Cambridge, MA 02138\n"
                "Contact-Name: Library Innovation Lab\n"
                "Contact-Email: lil@law.harvard.edu\n"
                "External-Description: Cases for %s\n"
                "Bagging-Date: %s\n"
            ) % (filter_item, timezone.now().strftime("%Y-%m-%d"))

            # fake Request object used for serializing cases with DRF's serializer
            vars['fake_request'] = namedtuple('Request', ['query_params', 'accepted_renderer'])(
                query_params={'body_format': format_name},
                accepted_renderer=None,
            )

            # set up paths for zip file output
            vars['internal_path'] = Path(dir_name + '-' + format_name)
            vars['data_file_path'] = Path('data', 'data.jsonl.xz')

            # create new zip file in memory
            vars['out_spool'] = SpooledTemporaryFile(max_size=2**30)
            vars['archive'] = zipfile.ZipFile(vars['out_spool'], 'w', zipfile.ZIP_STORED)
            vars['data_file'] = tempfile.NamedTemporaryFile()
            vars['hashing_data_file'] = HashingFile(vars['data_file'], 'sha512')
            vars['compressed_data_file'] = lzma.open(vars['hashing_data_file'], "w")

        # write each case
        for item in queryset:
            for format_name, vars in formats.items():
                serializer = BulkCaseSerializer(item, context={'request': vars['fake_request']})
                vars['compressed_data_file'].write(bytes(json.dumps(serializer.data), 'utf8'))
                vars['compressed_data_file'].write(b'\n')

        # finish bag for each format
        for format_name, vars in formats.items():
            # write temp data file to bag
            vars['compressed_data_file'].close()
            vars['data_file'].flush()
            vars['payload'].append("%s %s" % (vars['hashing_data_file'].hexdigest(), vars['data_file_path']))
            vars['archive'].write(vars['data_file'].name, str(vars['internal_path'] / vars['data_file_path']))
            vars['data_file'].close()

            # write bagit metadata files and close zip
            vars['archive'].writestr(str(vars['internal_path'] / "bagit.txt"), vars['bagit'])
            vars['archive'].writestr(str(vars['internal_path'] / "bag-info.txt"), vars['baginfo'])
            vars['archive'].writestr(str(vars['internal_path'] / "manifest-sha512.txt"), "\n".join(vars['payload']))
            vars['archive'].close()

            # copy temp file to django storage
            vars['out_spool'].seek(0)
            zip_name = str(vars['internal_path']) + '.zip'
            case_export = CaseExport(public=public, filter_id=filter_item.pk, filter_type=filter_item.__class__.__name__.lower(), body_format=format_name, file_name=zip_name)
            case_export.file.save(zip_name, File(vars['out_spool']))

    finally:
        # in case of error, make sure anything opened was closed
        for format_name, vars in formats.items():
            for file_handle in ('compressed_data_file', 'data_file', 'archive', 'out_spool'):
                try_to_close(vars.get(file_handle))

