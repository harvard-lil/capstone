import json
import re
from io import BytesIO
from multiprocessing import Pool, cpu_count
from pathlib import Path
from subprocess import run
import tarfile
from tempfile import TemporaryDirectory

from tqdm import tqdm

from capdb.models import normalize_cite
from capapi.documents import ResolveDocument
from scripts.simhash import get_simhash


def load_cluster(args):
    """
        Load a single CourtListener cluster with its opinions from disk, and return metadata.
        This is called within a process pool; see ingest_courtlistener for how it's used.
    """
    cluster_member, opinions_dir = args
    with cluster_member.open() as f:
        cluster = json.load(f)

    # skip clusters without citations
    if not cluster['citations']:
        return None

    # load text of all opinions for this cluster as a single string with html stripped, for simhashing
    opinion_texts = []
    for opinion_url in cluster['sub_opinions']:
        opinion_id = opinion_url.split('/')[-2]
        try:
            with opinions_dir.joinpath(f'{opinion_id}.json').open() as f:
                opinion = json.load(f)
        except FileNotFoundError:
            print("- Opinion file not found:", opinion_id)
            continue
        opinion_text = next((opinion[k] for k in
                             ['html_with_citations', 'plain_text', 'html', 'html_lawbox', 'html_columbia',
                              'xml_harvard'] if opinion[k]), '')
        opinion_texts.append(re.sub(r'<.+?>', '', opinion_text))

    # process citations
    citations = []
    for c in cluster['citations']:
        cite = f"{c['volume']} {c['reporter']} {c['page']}"
        try:
            page_int = int(c['page'])
        except (TypeError, ValueError):
            page_int = None
        citations.append({
            'cite': cite,
            'normalized_cite': normalize_cite(cite),
            'type': c['type'],
            'volume': c['volume'],
            'reporter': c['reporter'],
            'page': c['page'],
            'page_int': page_int,
        })

    # return metadata
    return {
        'id': f"cl-{cluster['id']}",
        'source': 'cl',
        'source_id': cluster['id'],
        'citations': citations,
        'name_short': cluster['case_name'],
        'name_full': cluster['case_name_full'],
        'decision_date': cluster['date_filed'],
        'frontend_url': 'https://www.courtlistener.com' + cluster['absolute_url'],
        'api_url': cluster['resource_uri'].replace(':80/', '/'),
        'simhash': get_simhash("\n".join(opinion_texts))
    }


def ingest_courtlistener(download_dir='/tmp', start_from=None):
    """ Download CourtListener cases and add metadata to citation resolver endpoint. """
    download_dir = Path(download_dir)
    opinions_file = download_dir / 'opinions.tar'
    clusters_file = download_dir / 'clusters.tar'
    if not opinions_file.exists():
        print("Downloading", opinions_file)
        run(f"wget -O {opinions_file} https://www.courtlistener.com/api/bulk-data/opinions/all.tar", shell=True)
    if not clusters_file.exists():
        print("Downloading", clusters_file)
        run(f"wget -O {clusters_file} https://www.courtlistener.com/api/bulk-data/clusters/all.tar", shell=True)

    # Courtlistener bulk files look like this:
    #     - clusters.tar
    #      - somejur.tar.gz
    #       - somecaseid.json
    #     - opinions.tar
    #      - somejur.tar.gz
    #       - someopinionid.json
    # Opinion IDs for each case are listed in the somecaseid.json files.
    # So the plan is to go through each jurisdiction, unpack the somejur.tar.gz files to disk, and then hand off the
    # list of somecaseid.json files to a process pool to ingest. Then we stream the results to Elasticsearch to index.
    with tarfile.open(clusters_file) as clusters_tar:
        jurisdiction_files = clusters_tar.getnames()
    pool = Pool(max(cpu_count() // 2, 1))
    for jurisdiction_file in jurisdiction_files:
        if start_from:
            if jurisdiction_file == start_from:
                start_from = None
            else:
                print("Skipping", jurisdiction_file)
                continue
        print("Ingesting", jurisdiction_file)
        with TemporaryDirectory() as tmpdir:
            clusters_dir = Path(tmpdir, "clusters")
            opinions_dir = Path(tmpdir, "opinions")
            clusters_dir.mkdir()
            opinions_dir.mkdir()
            run(f"tar -xOf {clusters_file} {jurisdiction_file} | tar -C {clusters_dir} -zxf -", shell=True)
            run(f"tar -xOf {opinions_file} {jurisdiction_file} | tar -C {opinions_dir} -zxf -", shell=True)
            documents = pool.imap_unordered(load_cluster, ((cluster_member, opinions_dir) for cluster_member in clusters_dir.glob("*.json")))
            ResolveDocument().update(tqdm(d for d in documents if d), parallel=True)


def make_test_files(input_dir='.', output_dir='test_data/courtlistener'):
    """ Create test files for scripts/tests/test_ingest_courtlistener.py """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    for fname in ('clusters.tar', 'opinions.tar'):
        with tarfile.open(input_dir / fname) as jurs_tar:
            jur_file = jurs_tar.extractfile('nm.tar.gz')
            with tarfile.open(fileobj=jur_file) as jur_tar:
                text = jur_tar.extractfile('891689.json').read()
        jur_buffer = BytesIO()
        with tarfile.open(output_dir / fname, 'w') as jurs_tar:
            with tarfile.open(fileobj=jur_buffer, mode='w:gz') as jur_tar:
                t = tarfile.TarInfo('891689.json')
                t.size = len(text)
                jur_tar.addfile(t, BytesIO(text))
            t = tarfile.TarInfo('nm.tar.gz')
            t.size = jur_buffer.tell()
            jur_buffer.seek(0)
            jurs_tar.addfile(t, jur_buffer)
