import boto3
import json
import os
import tempfile
from collections import namedtuple

from capapi.documents import CaseDocument
from capapi.serializers import NoLoginCaseDocumentSerializer, CaseDocumentSerializer
from capdb.models import Reporter, VolumeMetadata, CaseMetadata, CaseStructure

s3_client = boto3.client('s3')

def export_cases_by_reporter(redacted, reporter_id):
    """
        Write a .jsonl file with all cases per reporter.
    """
    # determine prefix based on a case's frontend_url
    reporter = Reporter.objects.get(pk=reporter_id)
    sample_case_obj = CaseMetadata.objects.select_related().filter(reporter = reporter_id)[0]
    frontend_url = sample_case_obj.frontend_url
    reporter_prefix = '/'.join(frontend_url.rsplit('/')[1:2])
    
    # set bucket name for all operations 
    if redacted:
        bucket = "cap-redacted"
    else:
        bucket = "cap-unredacted"

    # find the search object for all cases
    cases_search = CaseDocument.raw_search().filter("term", reporter__id=reporter_id)
    if cases_search.count() == 0:
        print("WARNING: Reporter '{}' contains NO CASES.".format(reporter.full_name))
        return
    
    formats = {
        'text': {
            'serializer': NoLoginCaseDocumentSerializer,
            'query_params': {'body_format': 'text'},
        },
        'metadata': {
            'serializer': CaseDocumentSerializer,
            'query_params': {},
        }
    }
    # set up vars for text format
    for format_name, vars in list(formats.items()):
        # fake Request object used for serializing cases with DRF's serializer
        vars['fake_request'] = namedtuple('Request', ['query_params', 'accepted_renderer'])(
            query_params=vars['query_params'],
            accepted_renderer=None,
        )
        # based on the format, create appropriate prefix
        if format_name == 'metadata':
            key = f'{reporter_prefix}/Metadata.json'
        else:
            key = f'{reporter_prefix}/Cases.jsonl'

        # store the serialized data
        with tempfile.NamedTemporaryFile() as file:
            for item in cases_search.scan():
                serializer = vars['serializer'](item['_source'], context={'request': vars['fake_request']})
                file.write(json.dumps(serializer.data).encode('utf-8') + b'\n')
            file.flush()

            s3_client.upload_file(
                Filename=file.name,
                Bucket=bucket,
                Key=key
            )
    
    # get volumes in reporter
    volumes = VolumeMetadata.objects.select_related().filter(reporter = reporter_id)
    # VolumeMetadata.raw_search().filter("term", reporter__id=reporter_id)
    for volume in volumes:
        # export volume metadata/url

        export_cases_by_volume(volumes, cases_search, frontend_url, bucket)

def export_cases_by_volume(volume, cases_search, frontend_url, bucket):
    """
        Write a .jsonl file with all cases per volume.
    """
    cases = CaseMetadata.objects.select_related().filter(volume__barcode = volume.barcode)
    if cases.count() == 0:
        print("WARNING: Volume '{}' contains NO CASES.".format(volume.barcode))
        return

    volume_prefix = '/'.join(frontend_url.rsplit('/')[1:-2])
    formats = {
        'text': {
            'serializer': NoLoginCaseDocumentSerializer,
            'query_params': {'body_format': 'text'},
        },
        'metadata': {
            'serializer': CaseDocumentSerializer,
            'query_params': {},
        }
    }

    # set up vars for text format
    for format_name, vars in list(formats.items()):
        # fake Request object used for serializing cases with DRF's serializer
        vars['fake_request'] = namedtuple('Request', ['query_params', 'accepted_renderer'])(
            query_params=vars['query_params'],
            accepted_renderer=None,
        )
        if format_name == 'metadata':
            key = f'{volume_prefix}/Metadata.json'
        else:
            key = f'{volume_prefix}/Cases.jsonl'
        
        # Store the serialized data
        with tempfile.NamedTemporaryFile() as file:
            for item in cases_search.scan():
                serializer = vars['serializer'](item['_source'], context={'request': vars['fake_request']})
                file.write(json.dumps(serializer.data).encode('utf-8') + b'\n')
            file.flush()

            s3_client.upload_file(
                Filename=file.name,
                Bucket=bucket,
                Key=key
            )
    # Export each case in the volume
    for case in cases:
        case_search = CaseDocument.raw_search().filter("term", id=case.id)
        # Get volume keys per volume dict
        export_single_case(case, case_search, f'{volume_prefix}/case', bucket)


def export_single_case(case, case_search, case_prefix, bucket):
    formats = {
        'text': {
            'serializer': NoLoginCaseDocumentSerializer,
            'query_params': {'body_format': 'text'},
        }
    }
    # find name of the paragraph that is tied to the case order from the volume PDF
    case_structure = CaseStructure.objects.select_related().filter(metadata_id = case.id)[0]
    
    case_name = case_structure.opinions[0]['paragraphs'][0]['id']
    breakpoint()
    # set up vars for text format
    for _, vars in list(formats.items()):
        # fake Request object used for serializing case with DRF's serializer
        vars['fake_request'] = namedtuple('Request', ['query_params', 'accepted_renderer'])(
            query_params=vars['query_params'],
            accepted_renderer=None,
        )
        key = f'{case_prefix}/{case_name}.json'
        
        # Store the serialized data
        with tempfile.NamedTemporaryFile() as file:
            for item in case_search.scan():
                serializer = vars['serializer'](item['_source'], context={'request': vars['fake_request']})
                file.write(json.dumps(serializer.data).encode('utf-8') + b'\n')
            file.flush()

            s3_client.upload_file(
                Filename=file.name,
                Bucket=bucket,
                Key=key
            )

       