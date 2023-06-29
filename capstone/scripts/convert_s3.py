import base64
import boto3
import hashlib
import json
import requests
import tempfile
from botocore.exceptions import ClientError
from collections import namedtuple

from capapi.documents import CaseDocument
from capapi.serializers import (
    ConvertCaseDocumentSerializer,
    ConvertNoLoginCaseDocumentSerializer,
)
from capdb.models import Reporter, VolumeMetadata, CaseMetadata

s3_client = boto3.client("s3")
api_endpoint = "https://api.case.law/v1/"

"""
This script must be run with boto3 1.26+ rather than the default 1.17.
"""


def put_volumes_reporters_on_s3(redacted: bool) -> None:
    """
    Save all reporter and volume metadata to files on S3.
    Kicks off the full cascading file creation series.
    """
    bucket = get_bucket_name(redacted)

    for file_type in ["reporters", "volumes"]:
        current_endpoint = f"{api_endpoint}{file_type}/"
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


def export_cases_to_s3(redacted: bool, reporter_id: str) -> None:
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
    put_reporter_metadata(bucket, reporter, reporter_prefix)

    # get volumes in reporter
    volumes = VolumeMetadata.objects.select_related().filter(reporter=reporter_id)
    # export volume metadata/cases
    export_cases_by_volume(volumes, bucket, redacted)


def export_cases_by_volume(volumes: list, dest_bucket: str, redacted: bool) -> None:
    """
    Write a .jsonl file with all cases per volume.
    Write a .jsonl file with all cases' metadata per volume.
    Write a .jsonl file with all volume metadata for this collection.
    """
    formats = {
        "text": {
            "serializer": ConvertNoLoginCaseDocumentSerializer,
            "query_params": {"body_format": "text"},
        },
        "metadata": {
            "serializer": ConvertCaseDocumentSerializer,
            "query_params": {},
        },
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

        for format_name, vars in list(formats.items()):
            # fake Request object used for serializing cases with DRF's serializer
            vars["fake_request"] = namedtuple(
                "Request", ["query_params", "accepted_renderer"]
            )(
                query_params=vars["query_params"],
                accepted_renderer=None,
            )

            if format_name == "metadata":
                key = f"{volume_prefix}/CasesMetadata.jsonl"
            else:
                key = f"{volume_prefix}/Cases.jsonl"

            # store the serialized case data in tempfile
            with tempfile.NamedTemporaryFile() as file:
                for item in cases_search.scan():
                    # pass case in to add additional data to the CaseDocument
                    case = CaseMetadata.objects.get(pk=item["_source"]["id"])
                    serializer = vars["serializer"](
                        item["_source"],
                        context={
                            "request": vars["fake_request"],
                            "first_page_order": case.first_page_order,
                            "last_page_order": case.last_page_order,
                        },
                    )
                    file.write(json.dumps(serializer.data).encode("utf-8") + b"\n")
                file.flush()
                # not closing with loop so I can continue using file for upload
                hash_and_upload(file, dest_bucket, key, "application/jsonl")

        # copies each volume PDF to new location if it doesn't already exist
        copy_volume_pdf(volume, volume_prefix, dest_bucket, redacted)

        # export each case in the volume
        for case in cases:
            export_single_case(case, f"{volume_prefix}/case", dest_bucket)


def export_single_case(case: object, case_prefix: str, bucket: str) -> None:
    """
    Put full text plus metadata of each case in reporterX/volumeX/case/caseX.jsonl.
    """
    # find name of the paragraph that is tied to the case order from the volume PDF

    # set up vars for text format
    vars = {
        "serializer": ConvertNoLoginCaseDocumentSerializer,
        "query_params": {"body_format": "text"},
    }
    # fake Request object used for serializing case with DRF's serializer
    vars["fake_request"] = namedtuple("Request", ["query_params", "accepted_renderer"])(
        query_params=vars["query_params"],
        accepted_renderer=None,
    )

    # select corresponding case search obj
    case_search = CaseDocument.raw_search().filter("term", id=case.id)
    # Store the serialized data
    with tempfile.NamedTemporaryFile() as file:
        for item in case_search.scan():
            serializer = vars["serializer"](
                item["_source"], context={"request": vars["fake_request"]}
            )
            file.write(json.dumps(serializer.data).encode("utf-8") + b"\n")
        # not closing with loop so I can continue using file for upload
        file.flush()
        # go back to the beginning so the hash generation works on the whole file
        file.seek(0)
        case_name = build_unique_case_name(case.first_page, bucket, case_prefix, file)
        if case_name is None:
            return
        else:
            key = f"{case_prefix}/{case_name}.json"
            hash_and_upload(file, bucket, key, "application/jsonl")


# Reporter-specific helper functions


def put_reporter_metadata(bucket: str, reporter: object, key: str) -> None:
    """
    Write a .json file with just the reporter metadata.
    """
    response = requests.get(f"{api_endpoint}reporters/{reporter.id}/")
    results = response.json()

    # add additional fields from reporter obj
    results["harvard_hollis_id"] = reporter.hollis
    results["nominative_for_id"] = reporter.nominative_for_id

    # remove unnecessary fields
    results.pop("url", None)
    results.pop("frontend_url", None)
    try:
        for jurisdiction in results["jurisdictions"]:
            jurisdiction.pop("slug", None)
            jurisdiction.pop("whitelisted", None)
            jurisdiction.pop("url", None)
    except KeyError as err:
        print(f"Cannot pop field {err} because 'jurisdictions' doesn't exist")

    with tempfile.NamedTemporaryFile() as file:
        file.write(json.dumps(results).encode("utf-8") + b"\n")
        file.flush()
        # not closing with loop so I can continue using file for upload
        hash_and_upload(
            file, bucket, f"{key}/ReporterMetadata.json", "application/json"
        )


# Volume-specific helper functions


def put_volumes_metadata(volumes: list, bucket: str, key: str) -> None:
    """
    Write a .jsonl file with the volume metadata for each volume in collection.
    """
    with tempfile.NamedTemporaryFile() as file:
        for volume in volumes:
            response = requests.get(f"{api_endpoint}volumes/{volume.barcode}/")
            results = response.json()

            file.write(json.dumps(results).encode("utf-8") + b"\n")
            file.flush()
            # not closing with loop so I can continue using file for upload
            hash_and_upload(
                file, bucket, f"{key}/VolumesMetadata.jsonl", "application/jsonl"
            )


def put_volume_metadata(bucket: str, volume: object, key: str) -> None:
    """
    Write a .json file with just the single volume metadata.
    """
    response = requests.get(f"{api_endpoint}volumes/{volume.barcode}/")
    results = response.json()
    # change "barcode" key to "id" key
    results["id"] = results.pop("barcode", None)

    # add additional fields from model
    results["harvard_hollis_id"] = volume.hollis_number
    results["spine_start_year"] = volume.spine_start_year
    results["spine_end_year"] = volume.spine_end_year
    results["publication_city"] = volume.publication_city
    results["second_part_of_id"] = volume.second_part_of_id

    # add information about volume's nominative_reporter
    if volume.nominative_reporter_id:
        reporter = Reporter.objects.get(pk=volume.nominative_reporter_id)
        results["nominative_reporter"] = {}
        results["nominative_reporter"]["id"] = volume.nominative_reporter_id
        results["nominative_reporter"]["short_name"] = reporter.short_name
        results["nominative_reporter"]["full_name"] = reporter.full_name
        results["nominative_reporter"][
            "volume_number"
        ] = volume.nominative_volume_number
    else:
        results["nominative_reporter"] = volume.nominative_reporter_id

    # remove unnecessary fields
    results.pop("reporter", None)
    results.pop("reporter_url", None)
    results.pop("url", None)
    results.pop("pdf_url", None)
    results.pop("frontend_url", None)
    try:
        for jurisdiction in results["jurisdictions"]:
            jurisdiction.pop("slug", None)
            jurisdiction.pop("whitelisted", None)
            jurisdiction.pop("url", None)
    except KeyError as err:
        print(f"Cannot pop field {err} because 'jurisdictions' doesn't exist")

    with tempfile.NamedTemporaryFile() as file:
        file.write(json.dumps(results).encode("utf-8") + b"\n")
        file.flush()
        # not closing with loop so I can continue using file for upload
        hash_and_upload(file, bucket, f"{key}/VolumeMetadata.json", "application/json")


def copy_volume_pdf(
    volume: object, volume_prefix: str, dest_bucket: str, redacted: bool
) -> None:
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
                f"Copied {source_prefix}/{volume.barcode}.pdf to \
                {volume_prefix}/Volume.pdf"
            )
        else:
            raise Exception(
                f"Cannot upload {source_prefix}/{volume.barcode}.pdf to \
                {volume_prefix}/Volume.pdf: %s"
                % err
            )


# Case-specific helper functions


def case_content_exists_in_s3(
    bucket: str, key: str, file: tempfile.TemporaryFile
) -> bool:
    """
    Check whether file with the same content already exists in S3 using
    ChecksumSHA256 hash comparison.
    """
    try:
        # Calculate the SHA256 hash of the file content
        file.seek(0)
        file_data = file.read()
        hash_object = hashlib.sha256(file_data)
        sha256_hash = base64.b64encode(hash_object.digest()).decode()

        # Get the object's metadata
        response = s3_client.get_object_attributes(
            Bucket=bucket, Key=key, ObjectAttributes=["Checksum"]
        )

        existing_hash = response.get("Checksum", {}).get("ChecksumSHA256")

        # Compare the hashes
        return existing_hash == sha256_hash

    except ClientError as err:
        if err.response["Error"]["Code"] == "404":
            return False
        else:
            raise Exception(f"Cannot check file {bucket}/{key}: %s" % err)


def build_unique_case_name(
    first_page: str, bucket: str, case_prefix: str, file: tempfile.TemporaryFile
) -> str:
    """
    Create unique case name based on first page
    """
    suffix = 1
    first_page = int(first_page)
    case_name = f"{first_page:04d}-{suffix:02d}"

    while case_name_exists(case_name, bucket, case_prefix):
        if case_content_exists_in_s3(bucket, f"{case_prefix}/{case_name}.json", file):
            print(f"Skipping {case_prefix}/{case_name}. Duplicate content.")
            return None
        suffix += 1
        case_name = f"{first_page:04d}-{suffix:02d}"

    return case_name


def case_name_exists(case_name: str, bucket: str, case_prefix: str) -> bool:
    """
    Find out whether the case name exists in S3
    """
    response = s3_client.list_objects_v2(
        Bucket=bucket, Prefix=f"{case_prefix}/{case_name}"
    )
    objects = response.get("Contents", [])
    return bool(objects)


# General helper functions


def hash_and_upload(
    file: tempfile.NamedTemporaryFile, bucket: str, key: str, content_type: str
) -> None:
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
            ContentType=content_type,
            ChecksumSHA256=sha256_hash,
        )
        print(f"Completed {key}")
    except ClientError as err:
        raise Exception(f"Error uploading {key}: %s" % err)


def get_bucket_name(redacted: bool) -> str:
    """
    Create bucket name based on redaction status
    """
    if redacted:
        bucket = "cap-redacted"
    else:
        bucket = "cap-unredacted"
    return bucket
