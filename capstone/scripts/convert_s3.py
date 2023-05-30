import base64
import boto3
import hashlib
import json
import requests
import tempfile
from botocore.exceptions import ClientError
from collections import namedtuple

from capapi.documents import CaseDocument
from capapi.serializers import NoLoginCaseDocumentSerializer, CaseDocumentSerializer
from capdb.models import Reporter, VolumeMetadata, CaseMetadata, CaseStructure

s3_client = boto3.client("s3")


# Doing this with the API because there are many fewer than cases
def put_volumes_reporters_on_s3(redacted):
    if redacted:
        bucket = "cap-redacted"
    else:
        bucket = "cap-unredacted"

    for file_type in ["reporters", "volumes"]:
        current_endpoint = f"https://api.case.law/v1/{file_type}/"
        previous_cursor = None
        current_cursor = ""
        with tempfile.NamedTemporaryFile() as file:
            while current_endpoint:
                response = requests.get(current_endpoint)
                results = response.json()
                # write each entry into jsonl
                for result in results["results"]:
                    file.write(json.dumps(result).encode("utf-8") + b"\n")
                    # for each reporter, kick off cascading export to S3
                    if file_type == "reporters":
                        export_cases_to_s3(redacted, result["id"])

                # update cursor to access next endpoint
                current_cursor = results["next"]
                if current_cursor != previous_cursor:
                    print("Update next to: ", current_cursor)

                previous_cursor = current_cursor
                current_endpoint = current_cursor
            file.flush()
            with open(file.name, "rb") as file:
                # read the file's contents
                file_data = file.read()
            try:
                s3_client.put_object(
                    Body=file_data, Bucket=bucket, Key=f"{file_type}.jsonl"
                )
            except ClientError as err:
                raise Exception(f"Error uploading {file_type}.jsonl: %s" % err)


def export_cases_to_s3(redacted, reporter_id):
    """
    Write a .jsonl file with all cases per reporter.
    """
    reporter = Reporter.objects.get(pk=reporter_id)

    # Make sure there are cases in the reporter
    cases_search = CaseDocument.raw_search().filter("term", reporter__id=reporter.id)
    if cases_search.count() == 0:
        print("WARNING: Reporter '{}' contains NO CASES.".format(reporter.full_name))
        return

    # determine prefix based on a case's frontend_url
    sample_case_obj = CaseMetadata.objects.select_related().filter(
        reporter=reporter_id
    )[0]
    frontend_url = sample_case_obj.frontend_url
    reporter_prefix = "/".join(frontend_url.rsplit("/")[1:2])

    # set bucket name for all operations
    if redacted:
        bucket = "cap-redacted"
    else:
        bucket = "cap-unredacted"

    formats = {
        "text": {
            "serializer": NoLoginCaseDocumentSerializer,
            "query_params": {"body_format": "text"},
        },
        "metadata": {
            "serializer": CaseDocumentSerializer,
            "query_params": {},
        },
    }
    # set up vars for text format
    for format_name, vars in list(formats.items()):
        # fake Request object used for serializing cases with DRF's serializer
        vars["fake_request"] = namedtuple(
            "Request", ["query_params", "accepted_renderer"]
        )(
            query_params=vars["query_params"],
            accepted_renderer=None,
        )
        # based on the format, create appropriate prefix
        if format_name == "metadata":
            # Add a [] around and , between for metadata
            key = f"{reporter_prefix}/Metadata.jsonl"
        else:
            key = f"{reporter_prefix}/Cases.jsonl"

        # store the serialized data
        with tempfile.NamedTemporaryFile() as file:
            for item in cases_search.scan():
                serializer = vars["serializer"](
                    item["_source"], context={"request": vars["fake_request"]}
                )
                file.write(json.dumps(serializer.data).encode("utf-8") + b"\n")
            file.flush()

            with open(file.name, "rb") as file:
                # read the file's contents
                file_data = file.read()
            # Calculate the SHA256 hash of the file data
            hash_object = hashlib.sha256(file_data)
            sha256_hash = base64.b64encode(hash_object.digest()).decode()

            # RETURN TO ADDRESS checksum that blows up if the tempfile created is not the same as the object uploaded
            try:
                s3_client.put_object(
                    Body=file_data,
                    Bucket=bucket,
                    Key=key,
                    ChecksumSHA256=sha256_hash,
                    ContentType="application/jsonl",
                )
            except ClientError as err:
                raise Exception(f"Error uploading {key}: %s" % err)
        print(f"Completed {key}")

    # get volumes in reporter
    volumes = VolumeMetadata.objects.select_related().filter(reporter=reporter_id)
    breakpoint()
    # export volume metadata/url
    export_cases_by_volume(volumes, bucket, redacted)


def export_cases_by_volume(volumes, dest_bucket, redacted):
    """
    Write a .jsonl file with all cases per volume.
    """
    formats = {
        "text": {
            "serializer": NoLoginCaseDocumentSerializer,
            "query_params": {"body_format": "text"},
        },
        "metadata": {
            "serializer": CaseDocumentSerializer,
            "query_params": {},
        },
    }

    # set up vars for text format
    for format_name, vars in list(formats.items()):
        # fake Request object used for serializing cases with DRF's serializer
        vars["fake_request"] = namedtuple(
            "Request", ["query_params", "accepted_renderer"]
        )(
            query_params=vars["query_params"],
            accepted_renderer=None,
        )

        for volume in volumes:
            # open each volume and put case text or metadata into file based on format
            cases_search = CaseDocument.raw_search().filter(
                "term", volume__barcode=volume.barcode
            )
            cases = CaseMetadata.objects.select_related().filter(
                volume__barcode=volume.barcode
            )
            frontend_url = cases[0].frontend_url

            if cases.count() == 0:
                print("WARNING: Volume '{}' contains NO CASES.".format(volume.barcode))
                return

            volume_prefix = "/".join(frontend_url.rsplit("/")[1:3])
            if format_name == "metadata":
                # Add a [] around and , between for metadata
                key = f"{volume_prefix}/Metadata.jsonl"
            else:
                key = f"{volume_prefix}/Cases.jsonl"

            # store the serialized case data in tempfile
            with tempfile.NamedTemporaryFile() as file:
                for item in cases_search.scan():
                    serializer = vars["serializer"](
                        item["_source"], context={"request": vars["fake_request"]}
                    )
                    file.write(json.dumps(serializer.data).encode("utf-8") + b"\n")
                file.flush()
                with open(file.name, "rb") as file:
                    # read the file's contents
                    file_data = file.read()
                # Calculate the SHA256 hash of the file data
                hash_object = hashlib.sha256(file_data)
                sha256_hash = base64.b64encode(hash_object.digest()).decode()

                # upload file to S3
                try:
                    s3_client.put_object(
                        Body=file_data,
                        Bucket=dest_bucket,
                        Key=key,
                        ChecksumSHA256=sha256_hash,
                        ContentType="application/jsonl",
                    )
                except ClientError as err:
                    raise Exception(f"Error uploading {key}: %s" % err)

            # uploads each volume PDF to same location
            if s3_client.head_object(
                Bucket=dest_bucket, Key=f"{volume_prefix}/Volume.pdf"
            ):
                print(f"{dest_bucket}/{volume_prefix}/Volume.pdf already uploaded!")
                pass
            else:
                upload_volume_to_s3(volume, volume_prefix, dest_bucket, redacted)

            # export each case in the volume
            for case in cases:
                export_single_case(case, f"{volume_prefix}/case", dest_bucket)


def export_single_case(case, case_prefix, bucket):
    # find name of the paragraph that is tied to the case order from the volume PDF
    case_structure = CaseStructure.objects.select_related().filter(metadata_id=case.id)[
        0
    ]
    case_name = case_structure.opinions[0]["paragraphs"][0]["id"]

    # set up vars for text format
    vars = {
        "serializer": NoLoginCaseDocumentSerializer,
        "query_params": {"body_format": "text"},
    }
    # fake Request object used for serializing case with DRF's serializer
    vars["fake_request"] = namedtuple("Request", ["query_params", "accepted_renderer"])(
        query_params=vars["query_params"],
        accepted_renderer=None,
    )
    key = f"{case_prefix}/{case_name}.json"

    # select corresponding case search obj
    case_search = CaseDocument.raw_search().filter("term", id=case.id)
    # Store the serialized data
    with tempfile.NamedTemporaryFile() as file:
        for item in case_search.scan():
            serializer = vars["serializer"](
                item["_source"], context={"request": vars["fake_request"]}
            )
            file.write(json.dumps(serializer.data).encode("utf-8") + b"\n")
        # Close the file
        file.flush()

        with open(file.name, "rb") as file:
            # read the file's contents
            file_data = file.read()
        # Calculate the SHA256 hash of the file data
        hash_object = hashlib.sha256(file_data)
        sha256_hash = base64.b64encode(hash_object.digest()).decode()

        # upload file to S3
        try:
            s3_client.put_object(
                Body=file_data,
                Bucket=bucket,
                Key=key,
                ChecksumSHA256=sha256_hash,
                ContentType="application/jsonl",
            )
        except ClientError as err:
            raise Exception(f"Error uploading {key}: %s" % err)


def upload_volume_to_s3(volume, volume_prefix, dest_bucket, redacted):
    if redacted:
        source_prefix = "pdf/redacted"
    else:
        source_prefix = "pdf/unredacted"

    # RETURN TO ADDRESS checksum that blows up if the object downloaded is not the same as the object uploaded
    try:
        source_pdf = s3_client.get_object(
            Bucket="harvard-cap-archive",
            Key=f"{source_prefix}/{volume.barcode}.pdf",
            ChecksumMode="ENABLED",
        )
    except ClientError as err:
        raise Exception(f"Error retrieving {source_prefix}/{volume.barcode}: %s" % err)

    s3_client.put_object(
        Body=source_pdf["Body"].read(),
        Bucket=dest_bucket,
        Key=f"{volume_prefix}/Volume.pdf",
    )
    print(f"Completed {volume_prefix}/{volume.barcode}.pdf")
