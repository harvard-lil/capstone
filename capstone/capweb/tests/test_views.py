from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import fitz
import pytest

from django.conf import settings

from capapi.tests.helpers import check_response, is_cached
from capdb.storages import DownloadOverlayStorage
from capweb.helpers import reverse
from test_data.test_fixtures.fixtures import CapClient


@pytest.mark.django_db
def test_docs(client, elasticsearch, three_cases):
    response = client.get(reverse('docs', args=['tutorials/api_tutorial']))
    check_response(response)

@pytest.mark.django_db
def test_docs_default(client, elasticsearch, three_cases):
    response = client.get(reverse('docs', args=['']))
    check_response(response, content_includes="Welcome to the Caselaw Access Project Documentation")


@pytest.mark.django_db
def test_legacy_redirect(client):
    response = client.get(reverse('api'))
    check_response(response, 302)
    assert "/docs/" in response.url


@pytest.mark.django_db
def test_download_area(client, auth_client, unlimited_auth_client, tmp_path, monkeypatch):
    overlay_path = Path(settings.BASE_DIR, 'downloads')
    underlay_path = tmp_path
    monkeypatch.setattr("capweb.views.download_files_storage", DownloadOverlayStorage(location=str(underlay_path)))

    # listing should include files from BASE_DIR/downloads as well as from donload_files_storage location
    underlay_path.joinpath('underlay.txt').write_text("contents")
    response = client.get(reverse('download-files', args=['']))
    check_response(response, content_type="application/json")
    response_json = response.json()
    assert set(f['name'] for f in response_json['files']) == (set(p.name for p in overlay_path.glob('*')) | {'underlay.txt'}) - {'README.md', '.DS_Store'}

    # can fetch contents from both overlay and underlay, with or without auth
    for c in (client, unlimited_auth_client):
        for read_from, path, content_type in ((overlay_path, 'README.md', 'text/markdown'), (underlay_path, 'underlay.txt', 'text/plain')):
            response = c.get(reverse('download-files', args=[path]))
            check_response(response, content_type=content_type, content_includes=read_from.joinpath(path).read_text())
            assert is_cached(response)

    # can list overlay folders
    response = c.get(reverse('download-files', args=['scdb/']))
    check_response(response, content_type="application/json")

    # restricted folder
    underlay_path.joinpath('restricted').mkdir()
    underlay_path.joinpath('restricted/file.txt').write_text('contents')
    for test_client, allow_downloads, token in (
            (client, False, 'none'),
            (auth_client, False, auth_client.auth_user.get_api_key()),
            (unlimited_auth_client, True, unlimited_auth_client.auth_user.get_api_key())
    ):
        token_client = CapClient()
        token_client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        for c in (test_client, token_client):
            # restricted directory
            response = c.get(reverse('download-files', args=['restricted/']))
            check_response(response, content_type="application/json")
            cacheable = c == client  # we can only cache for an anonymous user who didn't supply an auth header
            assert is_cached(response) is cacheable
            response_json = response.json()
            assert response_json['allow_downloads'] == allow_downloads
            assert set(f['name'] for f in response_json['files']) == {'file.txt'}

            # restricted file
            response = c.get(reverse('download-files', args=['restricted/file.txt']))
            assert not is_cached(response)
            if allow_downloads:
                check_response(response, content_type="text/plain", content_includes="contents")
            else:
                check_response(response, content_type="application/json", status_code=403)

    # symlinks
    underlay_path.joinpath('folder_link').symlink_to('restricted')
    underlay_path.joinpath('file_link.txt').symlink_to('restricted/file.txt')
    for p1, p2 in (('folder_link/', 'restricted/'), ('folder_link/file.txt', 'restricted/file.txt'), ('file_link.txt', 'restricted/file.txt')):
        response = c.get(reverse('download-files', args=[p1]))
        check_response(response, status_code=302)
        assert response.url == reverse('download-files', args=[p2])


@pytest.mark.django_db
def test_fetch(client, auth_client, elasticsearch, case_factory):
    cases = [
        case_factory(jurisdiction__whitelisted=True, first_page_order=1, last_page_order=2),
        case_factory(jurisdiction__whitelisted=False, first_page_order=1, last_page_order=2),
        case_factory(jurisdiction__whitelisted=False, first_page_order=1, last_page_order=2),
    ]
    cites = [c.citations.first() for c in cases]
    text = f"""
{cites[0].cite}
{"A"*50} {cites[1].cite} {"A"*50}
123 {cites[2].cite} 123
    """
    response = client.post(reverse('fetch'), {'q': text})
    check_response(response, content_includes=[
        cites[0].cite, cases[0].full_cite(),
        f'... {"A"*39}', cites[1].cite, cases[1].full_cite(), f'{"A"*29} ...',
        '    123', cites[2].cite, cases[2].full_cite(), ' 123\n',
    ])

    # can't download zip when logged out
    check_response(client.post(reverse('fetch'), {'download': '1', 'case_ids': [c.pk for c in cases]}), status_code=403)

    # can download zip of valid PDFs
    response = auth_client.post(reverse('fetch'), {'download': '1', 'case_ids': [c.pk for c in cases]})
    zip = ZipFile(BytesIO(b''.join(response)))
    for case in cases:
        path = 'cases/' + case.get_pdf_name()
        doc = fitz.open(stream=zip.open(path).read(), filetype='pdf')
        assert len(list(doc.pages())) == 2

    # quota is tracked
    auth_client.auth_user.refresh_from_db()
    assert auth_client.auth_user.case_allowance_remaining == 498
