import shutil
import tempfile
from pathlib import Path

import json
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from natsort import natsorted
from tqdm import tqdm

from capapi.documents import CaseDocument
from capapi.resources import call_serializer
from capapi.serializers import VolumeSerializer, NoLoginCaseDocumentSerializer, ReporterSerializer
from capdb.models import Reporter, VolumeMetadata, Jurisdiction, CaseMetadata
from capdb.tasks import record_task_status_for_volume
from capweb.helpers import select_raw_sql
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
    for reporter_dir in tqdm(dest_dir.iterdir()):
        if not reporter_dir.is_dir():
            continue
        reporter_metadata_path = reporter_dir / "ReporterMetadata.json"

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
        for volume in volumes_metadata:
            volume["reporter_slug"] = reporter_dir.name
        write_json(reporter_dir / "VolumesMetadata.json", volumes_metadata)

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
        jurisdictions[jurisdiction.id] = {
            "id": jurisdiction.pk,
            "slug": jurisdiction.slug,
            "name": jurisdiction.name,
            "name_long": jurisdiction.name_long,
            "reporters": [],
        }
        if jurisdiction.slug in jurisdiction_counts:
            jurisdictions[jurisdiction.id].update(jurisdiction_counts[jurisdiction.slug])

    for reporter in reporters_metadata:
        reporter_jurisdictions = reporter.pop("jurisdictions")
        for jurisdiction in reporter_jurisdictions:
            jurisdictions[jurisdiction["id"]]["reporters"].append(reporter)
    for jurisdiction_id in list(jurisdictions.keys()):
        if not jurisdictions[jurisdiction_id]["reporters"]:
            jurisdictions.pop(jurisdiction_id)

    jurisdictions = [j for j in sorted(jurisdictions.values(), key=lambda j: j["name_long"])]
    write_json(dest_dir / "JurisdictionsMetadata.json", jurisdictions)

    # write top-level VolumesMetadata.json
    print("Writing VolumesMetadata.json")
    all_volumes = []
    for v in dest_dir.glob('*/VolumesMetadata.json'):
        all_volumes.extend(json.loads(v.read_text()))
    write_json(dest_dir / "VolumesMetadata.json", all_volumes)


def crosscheck_reporters_dir(dest_dir: Path) -> None:
    """
    Check that all volumes in the database are in the expected location in dest_dir.
    Check expected case counts.
    Check expected reporter-level files.
    """
    volumes = VolumeMetadata.objects.exclude(out_of_scope=True).annotate(
        # add count of case_metadatas with in_scope = True
        case_count=Count('case_metadatas', filter=Q(case_metadatas__in_scope=True))
    ).select_related("reporter")
    reporter_dirs = set()
    # suspicious_volumes = []
    for volume in tqdm(volumes):
        if not volume.case_count:
            continue
        reporter_prefix, volume_prefix = get_prefixes(volume)
        reporter_dirs.add(reporter_prefix)
        volume_dir = dest_dir / reporter_prefix / volume_prefix
        if not volume_dir.exists():
            print(f"Volume {volume.barcode} is missing from {volume_dir}")
            continue
        volume_metadata = json.loads((volume_dir / "VolumeMetadata.json").read_text())
        if volume_metadata["id"] != volume.pk:
            print(f"Volume {volume.barcode} has mismatched id {volume_metadata['id']} in {volume_dir}.")
            continue
        case_count = len(list(volume_dir.glob("cases/*.json")))
        html_count = len(list(volume_dir.glob("html/*.html")))
        if case_count != volume.case_count:
            print(f"Volume {volume.barcode} has {case_count} cases in {volume_dir}, but {volume.case_count} in the database.")
        if html_count != case_count:
            print(f"Volume {volume.barcode} has {html_count} html files in {volume_dir}, but {case_count} cases.")
        if not (volume_dir / "CasesMetadata.json").exists():
            print(f"Volume {volume.barcode} is missing CasesMetadata.json in {volume_dir}")
        if not (volume_dir / "VolumeMetadata.json").exists():
            print(f"Volume {volume.barcode} is missing CasesMetadata.json in {volume_dir}")
    for reporter_prefix in reporter_dirs:
        reporter_dir = dest_dir / reporter_prefix
        for fname in ("ReporterMetadata.json", "VolumesMetadata.json"):
            if not (reporter_dir / fname).exists():
                print(f"Reporter {reporter_prefix} is missing {fname} in {reporter_dir}")


@shared_task(bind=True)
def export_cases_by_volume(self, volume_id: str, dest_dir: str) -> None:
    with record_task_status_for_volume(self, volume_id):
        volume = VolumeMetadata.objects.select_related("reporter").get(pk=volume_id)
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
        reporter_prefix, volume_prefix = get_prefixes(volume)
        prev_first_page = None
        case_file_name_index = 1
        cases = volume.case_metadatas.filter(in_scope=True).only("id", "first_page", "case_id")
        cases = natsorted(cases, key=lambda c: (c.first_page, c.case_id))
        for case in cases:
            if prev_first_page != case.first_page:
                case_file_name_index = 1
                prev_first_page = case.first_page
            else:
                case_file_name_index += 1
            case.static_file_name = f"/{reporter_prefix}/{volume_prefix}/{case.first_page:0>4}-{case_file_name_index:0>2}"
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
    reporter_prefix, volume_prefix = get_prefixes(volume)
    volume_dir = dest_dir / reporter_prefix / volume_prefix

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
    case_paths_by_id = dict(CaseMetadata.objects.filter(
        id__in=cited_case_ids,
        in_scope=True,
        volume__out_of_scope=False,
    ).exclude(static_file_name=None).values_list("id", "static_file_name"))

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
            # handle citations to documents outside our collection
            if "/citations/?q=" in el.attrib["href"]:
                el.set("href", "/citations/?q=" + el.attrib["href"].split("/citations/?q=", 1)[1])
                continue
            if "data-case-ids" not in el.attrib:
                # shouldn't happen
                continue
            el_case_paths = []
            el_case_ids = []
            for i in el.attrib["data-case-ids"].split(","):
                i = int(i)
                if i in case_paths_by_id:
                    el_case_paths.append(case_paths_by_id[i])
                    el_case_ids.append(i)
            if el_case_paths:
                el.attrib["href"] = el_case_paths[0]
                el.attrib["data-case-paths"] = ",".join(el_case_paths)
            else:
                el.attrib["href"] = ""
                el.attrib.pop("data-case-ids")
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


def get_prefixes(volume):
    reporter_prefix = reporter_slug_dict.get(volume.reporter_id, volume.reporter.short_name_slug)
    volume_prefix = (
        f"{volume.volume_number}-2" if volume.second_part_of_id
        else colliding_volumes[volume.pk] if volume.pk in colliding_volumes
        else volume.volume_number
    )
    return reporter_prefix, volume_prefix


def get_colliding_volumes():
    # find volumes that have identical reporter and volume number, and don't have second_part_of
    # this is either early N.C., which is known to be messed up, or A.3d where we got volumes
    # donated from Fastcase redundant with volumes we already had
    counts = {}
    lookup = {}
    for row in select_raw_sql("""
        SELECT v2.barcode AS id, v2.volume_number, v2.reporter_id
        FROM capdb_volumemetadata v1
        JOIN capdb_volumemetadata v2 ON v1.volume_number = v2.volume_number
                                      AND v1.reporter_id = v2.reporter_id
                                      AND v1.barcode < v2.barcode
        WHERE v1.out_of_scope = FALSE
        AND v2.out_of_scope = FALSE
        AND v1.second_part_of_id IS NULL
        AND v2.second_part_of_id IS NULL
        AND EXISTS (
            SELECT 1 FROM capdb_casemetadata c1
            WHERE c1.volume_id = v1.barcode
            AND c1.in_scope = TRUE
        )
        AND EXISTS (
            SELECT 1 FROM capdb_casemetadata c2
            WHERE c2.volume_id = v2.barcode
            AND c2.in_scope = TRUE
        )
        ORDER BY v2.barcode
    """, using="capdb"):
        if row.id in lookup:
            continue
        count_key = (row.reporter_id, row.volume_number)
        if count_key in counts:
            counts[count_key] += 1
        else:
            counts[count_key] = 1
        lookup[row.id] = f"{row.volume_number}-{1+counts[count_key]}"
    return lookup

# hardcoding this for now to avoid running get_colliding_volumes()
colliding_volumes = {'32044133499640': '60-2', 'A3d_138': '138-2', 'A3d_139': '139-2', 'A3d_140': '140-2', 'A3d_141': '141-2', 'A3d_142': '142-2', 'A3d_143': '143-2', 'A3d_144': '144-2', 'A3d_145': '145-2', 'A3d_146': '146-2', 'A3d_147': '147-2', 'A3d_148': '148-2', 'A3d_149': '149-2', 'A3d_150': '150-2', 'A3d_151': '151-2', 'A3d_152': '152-2', 'A3d_153': '153-2', 'A3d_154': '154-2', 'A3d_155': '155-2', 'A3d_156': '156-2', 'A3d_157': '157-2', 'A3d_158': '158-2', 'A3d_159': '159-2', 'A3d_160': '160-2', 'A3d_161': '161-2', 'A3d_162': '162-2', 'A3d_163': '163-2', 'A3d_164': '164-2', 'A3d_165': '165-2', 'A3d_166': '166-2', 'A3d_167': '167-2', 'A3d_168': '168-2', 'A3d_169': '169-2', 'A3d_170': '170-2', 'A3d_171': '171-2', 'A3d_172': '172-2', 'A3d_173': '173-2', 'A3d_174': '174-2', 'A3d_175': '175-2', 'A3d_176': '176-2', 'A3d_177': '177-2', 'A3d_178': '178-2', 'NOTALEPH000015': '5-2', 'NOTALEPH000021': '1-2', 'NOTALEPH000022': '4-2', 'NOTALEPH000032': '1-3'}
