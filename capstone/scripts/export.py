import json
import lzma
import tempfile
import zipfile
from io import StringIO
from collections import namedtuple
from datetime import date
from pathlib import Path
from celery import shared_task
from django.conf import settings

from django.template.loader import render_to_string
from django.utils import timezone

from capapi.documents import CaseDocument
from capapi.serializers import NoLoginCaseDocumentSerializer, CaseDocumentSerializer
from capdb.models import Jurisdiction, Reporter
from capdb.storages import writeable_download_files_storage
from scripts.helpers import HashingFile


def init_export(changelog):
    # setup vars
    version_string = date.today().strftime('%Y%m%d')
    template_dir = Path(settings.BASE_DIR, 'capdb/templates/bulk_export')
    output_path = Path('bulk_exports', version_string)
    if writeable_download_files_storage.exists(str(output_path / 'README.md')):
        print("Cannot init export; %s already exists" % output_path)
        return

    # write readme files
    print("Writing README files to %s" % output_path)
    for path in template_dir.rglob('*'):
        if path.is_dir():
            continue
        path = path.relative_to(template_dir)
        contents = render_to_string('bulk_export/%s' % path, {
            'changes': changelog,
            'export_date': date.today(),
        })
        writeable_download_files_storage.save('bulk_exports/%s/%s' % (version_string, path), StringIO(contents))

    # run export
    export_all(version_string)


def export_all(version_string):
    """
        Queue celery tasks to export all jurisdictions and reporters.
        If before_date is provided, only queue jobs where the last export's export_date was less than before_date.
    """
    for model, task in ((Jurisdiction, export_cases_by_jurisdiction), (Reporter, export_cases_by_reporter)):
        print("Queueing %s" % model.__name__)
        for item in model.objects.all():
            print("- Adding %s" % item)
            task.delay(version_string, item.pk)

@shared_task
def export_cases_by_jurisdiction(version_string, id):
    """
        Write a .jsonl.gz file with all cases for jurisdiction.
    """
    jurisdiction = Jurisdiction.objects.get(pk=id)
    cases = CaseDocument.raw_search().filter("term", jurisdiction__id=id)
    if cases.count() == 0:
        print("WARNING: Jurisdiction '{}' contains NO CASES.".format(jurisdiction.name))
        return
    out_path = Path(
        "bulk_exports",
        version_string,
        "by_jurisdiction",
        "{subfolder}",
        jurisdiction.slug,
        "%s_{case_format}_%s.zip" % (jurisdiction.slug, version_string)
    )
    export_case_documents(cases, out_path, jurisdiction, public=jurisdiction.whitelisted)

@shared_task
def export_cases_by_reporter(version_string, id):
    """
        Write a .jsonl.gz file with all cases for reporter.
    """
    reporter = Reporter.objects.get(pk=id)
    cases = CaseDocument.raw_search().filter("term", reporter__id=id)
    if cases.count() == 0:
        print("WARNING: Reporter '{}' contains NO CASES.".format(reporter.full_name))
        return
    out_path = Path(
        "bulk_exports",
        version_string,
        "by_reporter",
        "{subfolder}",
        reporter.short_name_slug,
        "%s_{case_format}_%s.zip" % (reporter.short_name_slug, version_string)
    )
    public = not reporter.case_metadatas.in_scope().filter(jurisdiction__whitelisted=False).exists()
    export_case_documents(cases, out_path, reporter, public=public)

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


def export_case_documents(cases, zip_path, filter_item, public=False):
    """
        Export cases in queryset to dir_name.zip.
        filter_item is the Jurisdiction or Reporter used to select the cases.
        public controls whether export is downloadable by non-researchers.
    """

    formats = {
        'xml': {
            'serializer': NoLoginCaseDocumentSerializer,
            'query_params': {'body_format': 'xml'},
        },
        'text': {
            'serializer': NoLoginCaseDocumentSerializer,
            'query_params': {'body_format': 'text'},
        },
        'metadata': {
            'serializer': CaseDocumentSerializer,
            'query_params': {},
        }
    }

    try:
        # set up vars for each format
        for format_name, vars in list(formats.items()):
            # set up paths for zip file output
            subfolder = 'case_metadata' if format_name == 'metadata' else 'case_text_open' if public else 'case_text_restricted'
            vars['out_path'] = str(zip_path).format(subfolder=subfolder, case_format=format_name)
            if writeable_download_files_storage.exists(vars['out_path']):
                print("File %s already exists; skipping." % vars['out_path'])
                del formats[format_name]
                continue
            vars['internal_path'] = Path(Path(vars['out_path']).stem)
            vars['data_file_path'] = Path('data', 'data.jsonl.xz')

            # set up bagit metadata files
            vars['payload'] = []
            vars['bagit'] = "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n"
            vars['baginfo'] = (
                "Source-Organization: Harvard Law School Library Innovation Lab\n"
                "Organization-Address: 1545 Massachusetts Avenue, Cambridge, MA 02138\n"
                "Contact-Name: Library Innovation Lab\n"
                "Contact-Email: info@case.law\n"
                "External-Description: Cases for %s\n"
                "Bagging-Date: %s\n"
            ) % (filter_item, timezone.now().strftime("%Y-%m-%d"))

            # fake Request object used for serializing cases with DRF's serializer
            vars['fake_request'] = namedtuple('Request', ['query_params', 'accepted_renderer'])(
                query_params=vars['query_params'],
                accepted_renderer=None,
            )

            # create new zip file in memory
            vars['out_spool'] = tempfile.TemporaryFile()
            vars['archive'] = zipfile.ZipFile(vars['out_spool'], 'w', zipfile.ZIP_STORED)
            vars['data_file'] = tempfile.NamedTemporaryFile()
            vars['hashing_data_file'] = HashingFile(vars['data_file'], 'sha512')
            vars['compressed_data_file'] = lzma.open(vars['hashing_data_file'], "w")

        # write each case
        for item in cases.scan():
            for format_name, vars in formats.items():
                serializer = vars['serializer'](item['_source'], context={'request': vars['fake_request']})
                vars['compressed_data_file'].write(bytes(json.dumps(serializer.data), 'utf8') + b'\n')

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

            # copy temp file to permanent storage
            vars['out_spool'].seek(0)
            writeable_download_files_storage.save(vars['out_path'], vars['out_spool'])
            vars['out_spool'].close()

    finally:
        # in case of error, make sure anything opened was closed
        for format_name, vars in formats.items():
            for file_handle in ('compressed_data_file', 'data_file', 'archive', 'out_spool'):
                try_to_close(vars.get(file_handle))
