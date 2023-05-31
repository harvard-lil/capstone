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
from capdb.models import Reporter, VolumeMetadata, CaseMetadata

s3_client = boto3.client("s3")


# Doing this with the API because there are many fewer than cases
def put_volumes_reporters_on_s3(redacted):
    bucket = get_bucket_name(redacted)

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
    Write .jsonl file with all cases per reporter.
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
    bucket = get_bucket_name(redacted)

    # upload reporter metadata
    put_reporter_metadata(bucket, reporter_id, reporter_prefix)

    vars = {
        "serializer": NoLoginCaseDocumentSerializer,
        "query_params": {"body_format": "text"},
    }

    # fake Request object used for serializing cases with DRF's serializer
    vars["fake_request"] = namedtuple("Request", ["query_params", "accepted_renderer"])(
        query_params=vars["query_params"],
        accepted_renderer=None,
    )
    # based on the format, create appropriate prefix
    key = f"{reporter_prefix}/Cases.jsonl"

    # store the serialized data
    with tempfile.NamedTemporaryFile() as file:
        for item in cases_search.scan():
            serializer = vars["serializer"](
                item["_source"], context={"request": vars["fake_request"]}
            )
            file.write(json.dumps(serializer.data).encode("utf-8") + b"\n")
        file.flush()
        hash_and_upload(file, bucket, key, "application/jsonl")
    print(f"Completed {key}")

    # get volumes in reporter
    volumes = VolumeMetadata.objects.select_related().filter(reporter=reporter_id)
    # export volume metadata/cases
    export_cases_by_volume(volumes, bucket, reporter_prefix, redacted)


def export_cases_by_volume(volumes, dest_bucket, reporter_prefix, redacted):
    """
    Write a .jsonl file with all cases per volume.
    Write a .jsonl file with all volume metadata for this collection.
    """
    vars = {
        "serializer": CaseDocumentSerializer,
        "query_params": {},
    }
    # TODO: Add in if we want to have the mid-level metadata accessible
    # put_volumes_metadata(volumes, dest_bucket, reporter_prefix)

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
        put_volume_metadata(dest_bucket, volume, volume_prefix)

        # fake Request object used for serializing cases with DRF's serializer
        vars["fake_request"] = namedtuple(
            "Request", ["query_params", "accepted_renderer"]
        )(
            query_params=vars["query_params"],
            accepted_renderer=None,
        )
        key = f"{reporter_prefix}/CasesMetadata.jsonl"

        # store the serialized case data in tempfile
        with tempfile.NamedTemporaryFile() as file:
            for item in cases_search.scan():
                serializer = vars["serializer"](
                    item["_source"], context={"request": vars["fake_request"]}
                )
                file.write(json.dumps(serializer.data).encode("utf-8") + b"\n")
            file.flush()

            hash_and_upload(file, dest_bucket, key, "application/jsonl")

        # copies each volume PDF to new location if it doesn't already exist
        copy_volume_pdf(volume, volume_prefix, dest_bucket, redacted)

        # export each case in the volume
        for case in cases:
            export_single_case(case, f"{volume_prefix}/case", dest_bucket)


def export_single_case(case, case_prefix, bucket):
    """
    Put full text plus metadata of each case in reporterX/volumeX/case/caseX.jsonl.
    """
    # find name of the paragraph that is tied to the case order from the volume PDF
    case_name = build_unique_case_name(case.first_page, bucket, case_prefix)

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

        hash_and_upload(file, bucket, key, "application/jsonl")


# Reporter-specific helper functions


def put_reporter_metadata(bucket, reporter_id, key):
    """
    Write a .json file with just the reporter metadata.
    """
    response = requests.get(f"https://api.case.law/v1/reporters/{reporter_id}/")
    results = response.json()

    with tempfile.NamedTemporaryFile() as file:
        file.write(json.dumps(results).encode("utf-8") + b"\n")
        file.flush()
        hash_and_upload(
            file, bucket, f"{key}/ReporterMetadata.json", "application/json"
        )


# Volume-specific helper functions


def put_volumes_metadata(volumes, bucket, key):
    """
    Write a .jsonl file with the volume metadata for each volume in collection.
    """
    with tempfile.NamedTemporaryFile() as file:
        for volume in volumes:
            response = requests.get(
                f"https://api.case.law/v1/volumes/{volume.barcode}/"
            )
            results = response.json()

            file.write(json.dumps(results).encode("utf-8") + b"\n")
            file.flush()
            hash_and_upload(
                file, bucket, f"{key}/VolumesMetadata.jsonl", "application/jsonl"
            )


def put_volume_metadata(bucket, volume, key):
    """
    Write a .json file with just the single volume metadata.
    """
    response = requests.get(f"https://api.case.law/v1/volumes/{volume.barcode}/")
    results = response.json()

    with tempfile.NamedTemporaryFile() as file:
        file.write(json.dumps(results).encode("utf-8") + b"\n")
        file.flush()
        hash_and_upload(file, bucket, f"{key}/VolumeMetadata.json", "application/json")


def copy_volume_pdf(volume, volume_prefix, dest_bucket, redacted):
    """
    Copy PDF volume from original location to destination bucket
    """
    if redacted:
        source_prefix = "pdf/redacted"
    else:
        source_prefix = "pdf/unredacted"

    try:
        s3_client.head_object(Bucket=dest_bucket, Key=f"{volume_prefix}/Volume.pdf")
        print(f"{dest_bucket}/{volume_prefix}/Volume.pdf already uploaded!")
    except ClientError as err:
        if err.response["Error"]["Code"] == "404":
            # "With a copy command, the checksum of the object is a direct checksum of the full object."
            # https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html
            copy_source = {
                "Bucket": "harvard-cap-archive",
                "Key": f"{source_prefix}/{volume.barcode}.pdf",
            }
            copy_object_params = {
                "Bucket": dest_bucket,
                "Key": f"{volume_prefix}/Volume.pdf",
                "CopySource": copy_source,
            }

            s3_client.copy_object(**copy_object_params)
            print(
                f"Copied {source_prefix}/{volume.barcode}.pdf to {volume_prefix}/Volume.pdf"
            )
        else:
            raise Exception(
                f"Cannot upload {source_prefix}/{volume.barcode}.pdf to {volume_prefix}/Volume.pdf: %s"
                % err
            )


# Case-specific helper functions


def build_unique_case_name(first_page, bucket, case_prefix):
    """
    Create unique case name based on first page
    """
    suffix = 1
    first_page = int(first_page)
    case_name = f"{first_page:04d}-{suffix:02d}"

    while case_name_exists(case_name, bucket, case_prefix):
        suffix += 1
        case_name = f"{first_page:04d}-{suffix:02d}"

    return case_name


def case_name_exists(case_name, bucket, case_prefix):
    """
    Find out whether the case name exists in S3
    """
    response = s3_client.list_objects_v2(
        Bucket=bucket, Prefix=f"{case_prefix}/{case_name}"
    )
    objects = response.get("Contents", [])
    return bool(objects)


# General helper functions


def hash_and_upload(file, bucket, key, content_type):
    """
    Hash created file and upload to S3
    """
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
            ContentType=f"{content_type}",
        )
    except ClientError as err:
        raise Exception(f"Error uploading {key}: %s" % err)


def get_bucket_name(redacted):
    """
    Create bucket name based on redaction status
    """
    if redacted:
        bucket = "cap-redacted"
    else:
        bucket = "cap-unredacted"
    return bucket
