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
    ConvertNoLoginCaseDocumentSerializer,
)
from capdb.models import Reporter

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

    reporter_prefix = f'{reporter.short_name_slug}-{reporter.id}'

    # set bucket name for all operations
    bucket = get_bucket_name(redacted)

    # upload reporter metadata
    put_reporter_metadata(bucket, reporter, reporter_prefix)

    # get in-scope volumes with volume numbers in each reporter
    for volume in reporter.volumes.exclude(volume_number=None).exclude(volume_number='').exclude(out_of_scope=True):
        # export volume metadata/cases
        export_cases_by_volume(volume, reporter_prefix, bucket, redacted)


def export_cases_by_volume(volume: object, reporter_prefix: str, dest_bucket: str, redacted: bool) -> None:
    """
    Write a .json file for each case per volume.
    Write a .jsonl file with all cases' metadata per volume.
    Write a .jsonl file with all volume metadata for this collection.
    """

    case_file_name_index = 1
    prev_case_first_page = None

    vars = {
        "serializer": ConvertNoLoginCaseDocumentSerializer,
        "query_params": {"body_format": "text"},
    }

    # open each volume and put case text or metadata into file based on format
    cases_search = CaseDocument.raw_search().filter(
        "term", volume__barcode=volume.barcode
    )
    cases = list(volume.case_metadatas.select_related().order_by("case_id"))

    if len(cases) == 0:
        print("WARNING: Volume '{}' contains NO CASES.".format(volume.barcode))
        return

    cases_by_id = {case.pk: case for case in cases}

    volume_prefix = f'{reporter_prefix}/{volume.volume_number}'
    put_volume_metadata(dest_bucket, volume, volume_prefix)

    cases_key = f"{volume_prefix}/Cases/"

    # fetch existing files to compare to what we have
    s3_contents_hash = fetch_s3_files(dest_bucket, cases_key)

    # fake Request object used for serializing case with DRF's serializer
    vars["fake_request"] = namedtuple("Request", ["query_params", "accepted_renderer"])(
        query_params=vars["query_params"],
        accepted_renderer=None,
    )
    # fake Request object used for serializing cases with DRF's serializer
    vars["fake_request"] = namedtuple("Request", ["query_params", "accepted_renderer"])(
        query_params={"body_format": "text"},
        accepted_renderer=None,
    )

    # create a metadata contents string to append case metadata content
    metadata_contents = b""

    # store the serialized case data in tempfile
    for item in cases_search.scan():
        with tempfile.NamedTemporaryFile() as file:
            # pass case in to add additional data to the CaseDocument
            case = cases_by_id[item["_source"]["id"]]

            serializer = vars["serializer"](
                item["_source"],
                context={
                    "request": vars["fake_request"],
                    "first_page_order": case.first_page_order,
                    "last_page_order": case.last_page_order,
                },
            )

            # add data to metadata_contents string without 'casebody'
            metadata_data = serializer.data
            metadata_data.pop("casebody", None)
            metadata_contents += json.dumps(metadata_data).encode("utf-8") + b"\n"

            # compose each case file with a hash
            case_contents = json.dumps(serializer.data).encode("utf-8") + b"\n"
            hash_object = hashlib.sha256(case_contents)
            case_contents_hash = base64.b64encode(hash_object.digest()).decode()

            # calculate case file name
            if prev_case_first_page == case.first_page:
                case_file_name_index += 1
            else:
                case_file_name_index = 1
            case_file_name = (
                f"{case.first_page.zfill(4)}-{str(case_file_name_index).zfill(2)}.json"
            )

            # set so we can use to determine multiple cases on single page
            prev_case_first_page = case.first_page

            # ignore cases that have already been uploaded
            if (
                case_contents_hash in s3_contents_hash
                and s3_contents_hash[case_contents_hash] == case_file_name
            ):
                s3_contents_hash.pop(case_contents_hash, None)
                print(f"Skipped {cases_key}{case_file_name}")
                continue
            else:
                file.write(case_contents)
                file.flush()
                hash_and_upload(
                    file,
                    dest_bucket,
                    f"{cases_key}{case_file_name}",
                    "application/jsonl",
                )

    with tempfile.NamedTemporaryFile() as file:
        file.write(metadata_contents)
        # not closing with loop so I can continue using file for upload
        file.flush()
        hash_and_upload(
            file,
            dest_bucket,
            f"{volume_prefix}/CasesMetadata.jsonl",
            "application/jsonl",
        )

    # copies each volume PDF to new location if it doesn't already exist
    copy_volume_pdf(volume, volume_prefix, dest_bucket, redacted)


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
        results["nominative_reporter"] = {}
        results["nominative_reporter"]["id"] = volume.nominative_reporter_id
        results["nominative_reporter"][
            "short_name"
        ] = volume.nominative_reporter.short_name
        results["nominative_reporter"][
            "full_name"
        ] = volume.nominative_reporter.full_name
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


def fetch_s3_files(bucket: str, key: str) -> dict:
    try:
        s3_contents_hash = {}
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=key)
    except ClientError as err:
        raise Exception(f"Cannot list objects {bucket}/{key}: %s" % err)
    if "Contents" not in response:
        return s3_contents_hash
    else:
        for case in response["Contents"]:
            case_file_name = case["Key"].split("/")[-1]
            # Get the object's metadata
            try:
                response = s3_client.get_object_attributes(
                    Bucket=bucket, Key=case["Key"], ObjectAttributes=["Checksum"]
                )

                existing_hash = response.get("Checksum", {}).get("ChecksumSHA256")
                s3_contents_hash[existing_hash] = case_file_name
            except ClientError as err:
                raise Exception(f"Cannot check file {bucket}/{case['Key']}: %s" % err)

    return s3_contents_hash


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
