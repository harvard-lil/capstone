import shutil
import tempfile
from pathlib import Path

import boto3
import json
from botocore.exceptions import ClientError
from celery import shared_task
from django.conf import settings
from django.db import transaction
from natsort import natsorted
from tqdm import tqdm

from capapi.documents import CaseDocument
from capapi.resources import call_serializer
from capapi.serializers import VolumeSerializer, NoLoginCaseDocumentSerializer, ReporterSerializer
from capdb.models import Reporter, VolumeMetadata, Jurisdiction, CaseMetadata
from scripts.helpers import parse_html, serialize_html
from scripts.update_snippets import get_map_numbers


# steps:
# - export volumes: fab export_cap_static_volumes calls export_cases_by_volume()
# - export reporter metadata: fab summarize_cap_static calls finalize_reporters()
# - (not in codebase yet) copy PDFs and captars from one part of S3 to another


def finalize_reporters(dest_dir: str) -> None:
    """
    """
    dest_dir = Path(dest_dir)
    for sub_dir in ("redacted", "unredacted"):
        if (dest_dir / sub_dir).exists():
            finalize_reporters_dir(dest_dir / sub_dir)

def finalize_reporters_dir(dest_dir: Path) -> None:

    # write missing reporter metadata
    print("Writing missing reporter metadata")
    all_volumes = []
    for reporter_dir in tqdm(dest_dir.iterdir()):
        if not reporter_dir.is_dir():
            continue
        reporter_metadata_path = reporter_dir / "ReporterMetadata.json"
        if reporter_metadata_path.exists():
            continue

        # fetch reporter object
        if reporter_dir.name in reporter_slug_dict_reverse:
            reporter = Reporter.objects.get(pk=reporter_slug_dict_reverse[reporter_dir.name])
        else:
            reporter = Reporter.objects.get(short_name_slug=reporter_dir.name)

        # export reporter metadata
        reporter_dict = call_serializer(ReporterSerializer, reporter)
        reporter_dict["harvard_hollis_id"] = reporter.hollis
        reporter_dict["slug"] = reporter_dir.name
        remove_keys(reporter_dict, ["url", "frontend_url", ("jurisdictions", ["slug", "whitelisted", "url"])])
        write_json(reporter_metadata_path, reporter_dict)

        # write reporter-level VolumesMetadata.json
        print("Writing VolumesMetadata.json")
        volumes_metadata = [json.loads(f.read_text()) for f in natsorted(reporter_dir.glob("*/VolumeMetadata.json"))]
        for volume in volumes_metadata: volume["reporter_slug"] = reporter_dir.name
        write_json(reporter_dir / "VolumesMetadata.json", volumes_metadata)
        all_volumes.extend(volumes_metadata)

    # write ReportersMetadata.json
    print("Writing ReportersMetadata.json")
    reporters_metadata = [json.loads(f.read_text()) for f in natsorted(dest_dir.glob("*/ReporterMetadata.json"))]
    write_json(dest_dir / "ReportersMetadata.json", reporters_metadata)

    # write JurisdictionsMetadata.json
    # this is the same data as ReportersMetadata.json, but with a list of reporters for each jurisdiction
    # instead of a list of jurisdictions for each reporter
    print("Writing JurisdictionsMetadata.json")
    jurisdictions = {}
    jurisdiction_counts = get_map_numbers()
    for jurisdiction in Jurisdiction.objects.all():
        if jurisdiction.slug not in jurisdiction_counts:
            continue
        jurisdictions[jurisdiction.id] = {
            "id": jurisdiction.pk,
            "slug": jurisdiction.slug,
            "name": jurisdiction.name,
            "name_long": jurisdiction.name_long,
            **jurisdiction_counts[jurisdiction.slug],
            "reporters": [],
        }

    for reporter in reporters_metadata:
        reporter_jurisdictions = reporter.pop("jurisdictions")
        for jurisdiction in reporter_jurisdictions:
            jurisdictions[jurisdiction["id"]]["reporters"].append(reporter)

    jurisdictions = [j for j in sorted(jurisdictions.values(), key=lambda j: j["name_long"])]
    write_json(dest_dir / "JurisdictionsMetadata.json", jurisdictions)

    # write top-level VolumesMetadata.json
    print("Writing VolumesMetadata.json")
    write_json(dest_dir / "VolumesMetadata.json", all_volumes)


@shared_task
def export_cases_by_volume(volume: str, dest_dir: str) -> None:
    volume = VolumeMetadata.objects.select_related("reporter").get(pk=volume)
    dest_dir = Path(dest_dir)
    export_volume(volume, dest_dir / "redacted")

    # export unredacted version of redacted volumes
    if settings.REDACTION_KEY and volume.redacted:
        # use a transaction to temporarily unredact the volume, then roll back
        with transaction.atomic('capdb'):
            volume.unredact(replace_pdf=False)
            export_volume(volume, dest_dir / "unredacted")
            transaction.set_rollback(True, using='capdb')


def set_case_static_file_names(missing_only=True) -> None:
    """
    Set static_file_name for all cases.
    If two cases start on page 123, they will be named '0123-01' and '0123-02'.
    """
    volumes = VolumeMetadata.objects.select_related("reporter").filter(out_of_scope=False)
    if missing_only:
        volumes = volumes.filter(case_metadatas__static_file_name=None).select_related('reporter').distinct()
    for volume in tqdm(volumes):
        reporter_prefix = reporter_slug_dict.get(volume.reporter_id, volume.reporter.short_name_slug)
        prev_first_page = None
        case_file_name_index = 1
        cases = list(volume.case_metadatas.filter(in_scope=True).order_by('case_id').only("id", "first_page"))
        for case in cases:
            if prev_first_page != case.first_page:
                case_file_name_index = 1
                prev_first_page = case.first_page
            else:
                case_file_name_index += 1
            case.static_file_name = f"/{reporter_prefix}/{volume.volume_number}/{case.first_page:0>4}-{case_file_name_index:0>2}"
        CaseMetadata.objects.bulk_update(cases, ["static_file_name"])


def export_volume(volume: VolumeMetadata, dest_dir: Path) -> None:
    """
    Write a .json file for each case per volume.
    Write an .html file for each case per volume.
    Write a .json file with all case metadata per volume.
    Write a .json file with all volume metadata for this collection.
    """
    # set up vars
    print("Exporting volume", volume.get_frontend_url())
    reporter_prefix = reporter_slug_dict.get(volume.reporter_id, volume.reporter.short_name_slug)
    volume_dir = dest_dir / reporter_prefix / volume.volume_number

    # don't overwrite existing volumes
    if volume_dir.exists():
        return

    # find cases to write
    cases = list(volume.case_metadatas.filter(in_scope=True).for_indexing().order_by('case_id'))
    if not cases:
        print(f"WARNING: Volume '{volume.barcode}' contains NO CASES.")
        return

    # fetch paths of cited cases
    cited_case_ids = {i for c in cases for e in c.extracted_citations.all() for i in e.target_cases or []}
    case_paths_by_id = dict(CaseMetadata.objects.filter(id__in=cited_case_ids).values_list("id", "static_file_name"))

    # set up temp volume dir
    temp_dir = tempfile.TemporaryDirectory()
    temp_volume_dir = Path(temp_dir.name)
    cases_dir = temp_volume_dir / "cases"
    cases_dir.mkdir()
    html_dir = temp_volume_dir / "html"
    html_dir.mkdir()
    volume_metadata = volume_to_dict(volume)
    write_json(temp_volume_dir / "VolumeMetadata.json", volume_metadata)

    # variables for case export loop
    case_metadatas = []
    case_doc = CaseDocument()

    # store the serialized case data
    for case in cases:
        if not case.static_file_name:
            raise Exception("All cases must have static_file_name set by fab set_case_static_file_names")

        # convert case model to search index format
        search_item = case_doc.prepare(case)
        search_item['last_updated'] = search_item['last_updated'].isoformat()
        search_item['decision_date'] = search_item['decision_date'].isoformat()

        # convert search index format to API format
        case_data = call_serializer(NoLoginCaseDocumentSerializer, search_item, {"body_format": "text"})

        # update case_data to match our output format:
        if "casebody" in case_data:
            case_data["casebody"] = case_data["casebody"]["data"]
        case_data["file_name"] = case.static_file_name.rsplit("/", 1)[-1]
        case_data["first_page_order"] = case.first_page_order
        case_data["last_page_order"] = case.last_page_order
        remove_keys(case_data, [
            "reporter",
            "volume",
            "url",
            "frontend_url",
            "frontend_pdf_url",
            "preview",
            ("court", ["slug", "url"]),
            ("jurisdiction", ["slug", "whitelisted", "url"]),
            ("analysis", ["random_bucket", "random_id"]),
        ])
        for cite in case_data["cites_to"]:
            cite["opinion_index"] = cite.pop("opinion_id")
            if "case_ids" in cite:
                cite["case_paths"] = [case_paths_by_id[i] for i in cite["case_ids"] if i in case_paths_by_id]

        # fake dates for consistent test files
        if settings.TESTING:
            case_data["last_updated"] = "2023-12-01T01:01:01.0000001+00:00"
            case_data["provenance"]["date_added"] = "2023-12-01"

        # write casefile
        write_json(cases_dir / (case_data["file_name"] + ".json"), case_data)

        # write metadata without 'casebody'
        case_data.pop("casebody", None)
        case_metadatas.append(case_data)

        # write html file
        # update the urls inserted by scripts.extract_cites.extract_citations()
        html = search_item["casebody_data"]["html"]
        pq_html = parse_html(html)
        for el in pq_html("a.citation"):
            el_case_paths = []
            if "data-case-ids" in el.attrib:
                el_case_ids = [int(i) for i in el.attrib["data-case-ids"].split(",")]
                el_case_paths = [case_paths_by_id[i] for i in el_case_ids if i in case_paths_by_id]
            if el_case_paths:
                el.attrib["href"] = el_case_paths[0]
                el.attrib["data-case-paths"] = ",".join(el_case_paths)
            elif "/citations/?q=" in el.attrib["href"]:
                el.attrib["href"] = "/citations/?q=" + el.attrib["href"].split("/citations/?q=", 1)[1]
            else:
                el.attrib["href"] = ""
        html_file_path = html_dir / (case_data["file_name"] + ".html")
        html_file_path.write_text(serialize_html(pq_html))

    # write metadata file
    write_json(temp_volume_dir / "CasesMetadata.json", case_metadatas)

    # move to real directory
    volume_dir.parent.mkdir(exist_ok=True, parents=True)
    shutil.copytree(temp_volume_dir, volume_dir)


def volume_to_dict(volume: VolumeMetadata) -> dict:
    """
    Write a .json file with just the single volume metadata.
    """
    volume_data = call_serializer(VolumeSerializer, volume)

    # change "barcode" key to "id" key
    volume_data["id"] = volume_data.pop("barcode", None)

    # add additional fields from model
    volume_data["harvard_hollis_id"] = volume.hollis_number
    volume_data["spine_start_year"] = volume.spine_start_year
    volume_data["spine_end_year"] = volume.spine_end_year
    volume_data["publication_city"] = volume.publication_city
    volume_data["second_part_of_id"] = volume.second_part_of_id
    volume_data["redacted"] = volume.redacted

    # add information about volume's nominative_reporter
    if volume.nominative_reporter_id:
        volume_data["nominative_reporter"] = {
            "id": volume.nominative_reporter_id,
            "short_name": volume.nominative_reporter.short_name,
            "full_name": volume.nominative_reporter.full_name,
            "volume_number": volume.nominative_volume_number
        }
    elif volume.nominative_volume_number or volume.nominative_name:
        volume_data["nominative_reporter"] = {
            "volume_number": volume.nominative_volume_number,
            "nominative_name": volume.nominative_name,
        }
    else:
        volume_data["nominative_reporter"] = None

    # remove unnecessary fields
    remove_keys(volume_data, [
        "reporter",
        "reporter_url",
        "url",
        "pdf_url",
        "frontend_url",
        "nominative_volume_number",
        "nominative_name",
        ("jurisdictions", ["slug", "whitelisted", "url"]),
    ])

    return volume_data


def copy_volume_pdf(
    volume: object, volume_prefix: str, dest_bucket: str, redacted: bool
) -> None:
    """
    Copy PDF volume from original location to destination bucket
    """
    s3_client = boto3.client("s3")

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



### helpers ###

# Some reporters share a slug, so we have to differentiate with ids
reporter_slug_dict = {
    415: "us-ct-cl",
    657: "wv-ct-cl",
    580: "mass-app-div-annual",
    576: "mass-app-div",
}
reporter_slug_dict_reverse = {v: k for k, v in reporter_slug_dict.items()}

def remove_keys(results: dict, keys: list) -> dict:
    """
    Remove keys from results dict
    """
    for key in keys:
        if type(key) is tuple:
            key, subkeys = key
            if key in results:
                value = results[key]
                if type(value) is list:
                    for subvalue in value:
                        remove_keys(subvalue, subkeys)
                else:
                    remove_keys(value, subkeys)
        else:
            results.pop(key, None)
    return results

def write_json(path: Path, contents) -> None:
    """
    Write contents to path
    """
    path.write_text(json.dumps(contents, indent=2) + "\n")
