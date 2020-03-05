import io
import os
import csv
import json
import subprocess
from collections import OrderedDict
from pathlib import Path
from wsgiref.util import FileWrapper
from natsort import natsorted

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core import signing
from django.core.signing import Signer
from django.http import HttpResponseRedirect, HttpResponse, Http404, \
    HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import render
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.http import is_safe_url
from django.views import View
from django.utils.safestring import mark_safe

from capweb.forms import ContactForm
from capweb.helpers import get_data_from_lil_site, reverse, send_contact_email, render_markdown, is_browser_request, \
    page_image_url, safe_domains
from capweb.models import GallerySection

from capdb.models import Snippet, Court, Reporter, Jurisdiction
from capdb.storages import download_files_storage
from capapi.resources import form_for_request
from capapi.documents import CaseDocument
from config.logging import logger

from elasticsearch.exceptions import NotFoundError


def index(request):
    news = get_data_from_lil_site(section="news")
    federal = {
        "cases": 1693904,
        "reporters": 32,
        "pages_scanned": 9547364,
    }

    state = {
        "cases": "6.7M",
        "reporters": "627",
        "pages_scanned": "40M",
    }

    return render(request, "index.html", {
        'mailchimp_u': settings.MAILCHIMP['u'],
        'mailchimp_id': settings.MAILCHIMP['id'],
        'news': news[0:5],
        'state': state,
        'federal': federal,
        'page_image': 'img/og_image/index.png',
        'page_name': 'home'
    })


def about(request):
    contributors = get_data_from_lil_site(section="contributors")
    sorted_contributors = {}
    for contributor in contributors:
        sorted_contributors[contributor['sort_name']] = contributor
        if contributor['affiliated']:
            sorted_contributors[contributor['sort_name']]['hash'] = contributor['name'].replace(' ', '-').lower()
    sorted_contributors = OrderedDict(sorted(sorted_contributors.items()), key=lambda t: t[0])

    markdown_doc = render_to_string("about.md", {
        "contributors": sorted_contributors,
        "news": get_data_from_lil_site(section="news"),
        "email": settings.DEFAULT_FROM_EMAIL
    }, request)

    # render markdown document to html
    html, toc, meta = render_markdown(markdown_doc)

    meta = {k: mark_safe(v) for k, v in meta.items()}
    return render(request, "layouts/full.html", {
        'main_content': mark_safe(html),
        'sidebar_menu_items': mark_safe(toc),
        **meta,
    })


def contact(request):
    form = form_for_request(request, ContactForm)

    if request.method == 'POST' and form.is_valid():
        data = form.data
        # Only send email if box2 is filled out and box1 is not.
        # box1 is display: none, so should never be filled out except by spam bots.
        if data.get('box2') and not data.get('box1'):
            send_contact_email(data.get('subject'), data.get('box2'), data.get('email'))
            logger.info("sent contact email: %s" % data)
        else:
            logger.info("suppressing invalid contact email: %s" % data)
        return HttpResponseRedirect(reverse('contact-success'))

    email_from = request.user.email if request.user.is_authenticated else ""
    form.initial = {"email": email_from}

    return render(request, 'contact.html', {
        "form": form,
        "email": settings.DEFAULT_FROM_EMAIL,
        'page_image': 'img/og_image/contact.png',
        'meta_description': 'Email us at %s or fill out this form. ' % settings.DEFAULT_FROM_EMAIL,
    })


def tools(request):
    extra_context = {}
    markdown_doc = render_to_string("tools.md", extra_context, request)
    html, toc, meta = render_markdown(markdown_doc)
    meta = {k: mark_safe(v) for k, v in meta.items()}
    return render(request, "layouts/full.html", {
        'main_content': mark_safe(html),
        'sidebar_menu_items': mark_safe(toc),
        **meta,
    })


def gallery(request):
    sections = GallerySection.objects.prefetch_related('entries').order_by('order')
    return render(request, 'gallery.html', {
        'sections': sections,
        'email': settings.DEFAULT_FROM_EMAIL,
        'page_image': 'img/og_image/gallery.png',
        'meta_description': 'Sky is the limit! Here are some examples of what’s possible.'
    })



def maintenance_mode(request):
    return render(request, "error_page.html", {
        "type": "Maintenance",
        "title": "${title}",
        "middle": "${middle}",
        "bottom": "${bottom}",
        "action": "${action}",
        'page_image': 'img/og_image/api.png',
        'meta_description': 'This page is broken. Let us know if this should be working.'
    })


def wordclouds(request):
    wordclouds = sorted(path.name for path in Path(settings.BASE_DIR, 'static/img/wordclouds').glob('*.png'))
    return render(request, "gallery/wordclouds.html", {
        "wordclouds": wordclouds,
        'page_image': 'img/og_image/wordclouds.png',
        'meta_description': 'Most used words in California caselaw from 1853 to 2015'
    })


def limericks(request):
    return render(request, 'gallery/limericks.html', {
        'page_image': 'img/og_image/limericks.png',
        'meta_description': 'Generate rhymes using caselaw!'
    })


def api(request):
    try:
        case = CaseDocument.get(id=settings.API_DOCS_CASE_ID)
    except NotFoundError:
        try:
            case = CaseDocument.search().execute()[0]
        except NotFoundError:
            case = None

    markdown_doc = render_to_string("api.md", {"case": case}, request)

    # render markdown document to html
    html, toc, meta = render_markdown(markdown_doc)

    meta = {k: mark_safe(v) for k, v in meta.items()}
    return render(request, "layouts/full.html", {
        'main_content': mark_safe(html),
        'sidebar_menu_items': mark_safe(toc),
        **meta,
    })



def search_docs(request):
    return render(request, 'search_docs.md')


def snippet(request, label):
    snippet = get_object_or_404(Snippet, label=label).contents
    return HttpResponse(snippet, content_type=snippet.format)


class MarkdownView(View):
    """
        Render template_name as markdown, and then pass 'main_content', 'sidebar_menu_items', and 'meta' to base_template_name
        for display as HTML.

        IMPORTANT: As all outputs are marked safe, subclasses should never include user-generated input in the template context.
    """
    base_template_name = "layouts/full.html"
    extra_context = {}
    template_name = None

    def get(self, request, *args, **kwargs):
        # render any django template tags in markdown document
        markdown_doc = render_to_string(self.template_name, self.extra_context, request)

        # render markdown document to html
        html, toc, meta = render_markdown(markdown_doc)

        # present markdown html within base_template_name
        meta = {k:mark_safe(v) for k,v in meta.items()}
        return render(request, self.base_template_name, {
            'main_content': mark_safe(html),
            'sidebar_menu_items': mark_safe(toc),
            'main_content_style': 'markdown',
            **self.extra_context,
            **meta,
        })


def screenshot(request):
    """
        Return screenshot of a given URL on this site. This is a light wrapper around "node scripts/screenshot.js".

        Do not generate URLs for this page directly, but by calling page_image_url(). This view requires a signed JSON
        object within the ?payload= query parameter so it can't be called unexpectedly.
    """
    if not settings.SCREENSHOT_FEATURE:
        raise Http404

    # read payload
    try:
        payload = json.loads(Signer().unsign(request.GET.get('payload', '')))
    except signing.BadSignature:
        return HttpResponseBadRequest()

    ### NOTE: after this point, contents of 'payload' are verified as coming from a signed request we created,
    # though the 'url' parameter may be partially user-controlled. ###

    # validate that submitted URL is a complete URL on our site
    url = payload.get('url')
    if not url:
        return HttpResponseBadRequest("URL parameter required.")
    if not url.startswith('https://' if settings.MAKE_HTTPS_URLS else 'http://'):
        return HttpResponseBadRequest("Invalid URL protocol.")
    if not is_safe_url(url, safe_domains):
        return HttpResponseBadRequest("URL should match one of these domains: %s" % safe_domains)

    # apply target= and wait= query params
    command_args = []
    for selector in payload.get('waits', []):
        command_args += ['--wait', selector]
    for selector in payload.get('targets', []):
        command_args += ['--target', selector]
    timeout = payload.get('timeout', settings.SCREENSHOT_DEFAULT_TIMEOUT)

    # disable puppeteer sandbox just for dockerized dev/test env
    # this is needed because puppeteer can't run as root without --no-sandbox; the alternative would be to set up docker
    # to not run as root
    if os.environ.get('DOCKERIZED') and settings.DEBUG:
        command_args += ['--no-sandbox']

    # get screenshot from node scripts/screenshot.js
    subprocess_args = ['node', os.path.join(settings.BASE_DIR, 'scripts/screenshot.js'), '-m', str(timeout * 1000)] + command_args + [url]
    print(" ".join(subprocess_args))
    try:
        screenshot = subprocess.check_output(subprocess_args, timeout=timeout)
        content_type = "image/png"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print("Using fallback for screenshot with payload %s: %s" % (payload, e))
        fallback_path = payload.get('fallback')
        if not fallback_path or not staticfiles_storage.exists(fallback_path):
            fallback_path = 'img/og_image/api.jpg'
        with staticfiles_storage.open(fallback_path) as screenshot_file:
            screenshot = screenshot_file.read()
        content_types_by_suffix = {'png': 'image/png', 'jpg': 'image/jpeg'}
        content_type = content_types_by_suffix[fallback_path.rsplit('.', 1)[1]]

    return HttpResponse(screenshot, content_type=content_type)


def download_files(request, filepath=""):
    """
    If directory requested: show list of files inside dir
    If file requested: download file
    """

    if "manifest.csv" in filepath or "manifest.json" in filepath:
        return download_manifest_file(request, filepath=filepath)

    absolute_path = download_files_storage.path(filepath)

    allow_downloads = "restricted" not in absolute_path or request.user.unlimited_access_in_effect()

    # file requested
    if download_files_storage.isfile(filepath):

        if not allow_downloads:
            context = {
                "filename": filepath,
                "error": "If you believe you should have access to this file, "
                         "please let us know at <a href='mailto:info@case.law'>info@case.law</a>.",
                "title": "403 - Access to this file is restricted",
            }
            return render(request, "file_download_400.html", context, status=403)

        import magic
        mime = magic.Magic(mime=True)
        content_type = mime.from_file(absolute_path)
        chunk_size = 8192

        response = StreamingHttpResponse(FileWrapper(open(absolute_path, 'rb'), chunk_size), content_type=content_type)
        response['Content-Length'] = download_files_storage.size(absolute_path)

        return response

    # directory requested
    elif download_files_storage.isdir(filepath):
        if filepath and not filepath.endswith('/'):
            return HttpResponseRedirect(reverse('download-files', args=[filepath+'/']))

        # create clickable breadcrumbs
        breadcrumb_parts = filepath.split('/')

        breadcrumbs = []
        for idx, breadcrumb in enumerate(breadcrumb_parts):
            if breadcrumb:
                breadcrumbs.append({'name': breadcrumb,
                                    'path': "/".join(breadcrumb_parts[0:idx + 1])})

        readme = ""
        files = []
        for filename in list(download_files_storage.iter_files(filepath)):
            if "README.md" in filename:
                with open(download_files_storage.path(filename), "r") as f:
                    readme_content = f.read()
                readme, toc, meta = render_markdown(readme_content)
                continue

            is_dir = download_files_storage.isdir(filename)
            fileobject = {
                "name": filename.split('/')[-1],
                "path": filename + ('/' if is_dir else ''),
                "is_dir": is_dir,
                "size": download_files_storage.size(filename)
            }

            files.append(fileobject)

        # if we're  in the root folder, also add a manifest.csv
        if filepath == "":
            files.append({
                "name": "manifest.csv",
                "path": "manifest.csv",
                "is_dir": False,
            })
            files.append({
                "name": "manifest.json",
                "path": "manifest.json",
                "is_dir": False,
            })


        # sort files alphabetically
        files = natsorted(files, key=lambda x: x["name"].lower())

        context = {
            'files': files,
            'allow_downloads': allow_downloads,
        }

        if len(breadcrumbs) > 0:
            # Add home path to root folder if breadcrumbs exist
            context['breadcrumbs'] = [{'name': 'home', 'path': ''}] + breadcrumbs
        if readme:
            context['readme'] = mark_safe(readme)

        if is_browser_request(request):
            return render(request, "file_download.html", context)
        else:
            return HttpResponse(json.dumps(context), content_type='application/json')

    # path does not exist
    else:
        context = {
            "title": "404 - File not found",
            "error": "This file was not found in our system."
        }
        if is_browser_request(request):
            return render(request, "file_download_400.html", context, status=404)
        else:
            return HttpResponse(json.dumps(context), content_type='application/json')


def download_manifest_file(request, filepath=""):
    filename = "manifest"
    absolute_path = download_files_storage.path(filepath)
    manifest_dir = absolute_path.split('%s.' % filename)[0]

    def get_file_info(abs_filepath):
        fp = download_files_storage.relpath(abs_filepath)
        return {
            "path": fp,
            "size": download_files_storage.size(fp),
            "last_modified": download_files_storage.get_modified_time(fp).isoformat()}

    # send back file for downloading
    fieldnames = ["path", "size", "last_modified"]

    # if csv requested
    if "%s.csv" % filename in filepath:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for root, dirs, files in os.walk(manifest_dir):
            for name in files:
                writer.writerow(get_file_info(os.path.join(root, name)))
            for name in dirs:
                writer.writerow(get_file_info(os.path.join(root, name)))
        response = HttpResponse(output.getvalue(), content_type='text/csv')

    # if json requested
    elif "%s.json" % filename in filepath:
        all_files = []
        for root, dirs, files in os.walk(manifest_dir):
            for name in files:
                all_files.append(get_file_info(os.path.join(root, name)))
            for name in dirs:
                all_files.append(get_file_info(os.path.join(root, name)))
        response = HttpResponse(json.dumps(all_files), content_type='application/json')

    # if another file requested
    else:
        context = {
            "title": "404 - File not found",
            "error": "This file was not found in our system."
        }
        if is_browser_request(request):
            response = render(request, "file_download_400.html", context, status=404)
        else:
            response = HttpResponse(json.dumps(context), content_type='application/json')

    return response


def view_jurisdiction(request, jurisdiction_id):
    jurisdiction = get_object_or_404(Jurisdiction, pk=jurisdiction_id)

    fields = OrderedDict([
        ("ID", jurisdiction.id),
        ("Name", jurisdiction.name),
        ("Long Name", jurisdiction.name_long),
        ("Slug", jurisdiction.slug),
        ("whitelisted", jurisdiction.whitelisted),
    ])
    return render(request, "view_metadata.html", {
        'fields': fields,
        'type': 'jurisdiction',
        'title': jurisdiction.name
    })


def view_reporter(request, reporter_id):
    reporter = get_object_or_404(Reporter, pk=reporter_id)
    fields = OrderedDict([
        ("ID", reporter.id),
        ("Full Name", reporter.full_name),
        ("Short Name", reporter.short_name),
        ("Start Year", reporter.start_year),
        ("End Year", reporter.end_year),
        ("Volume Count", reporter.volume_count),
    ])

    return render(request, "view_metadata.html", {
        'fields': fields,
        'type': 'reporter',
        'title': reporter.short_name
    })


def view_court(request, court_id):
    court = get_object_or_404(Court, pk=court_id)
    fields = OrderedDict([
        ("ID", court.id),
        ("Name", court.name),
        ("Name Abbreviation", court.name_abbreviation),
        ("Jurisdiction", court.jurisdiction.name),
        ("Slug", court.slug),
    ])

    return render(request, "view_metadata.html", {
        'fields': fields,
        'type': 'court',
        'title': court.name_abbreviation
    })


def search(request):
    return render(request, "search.html")


def trends(request):
    q = request.GET.get('q')
    if q:
        title_suffix = ' for "%s"' % q
    else:
        title_suffix = ''
    if settings.SCREENSHOT_FEATURE:
        page_image = page_image_url(request.build_absolute_uri(), targets=['.graph-container'], waits=['#screenshot-ready'])
    else:
        page_image = None
    return render(request, "trends.html", {
        'title': 'Historical Trends' + title_suffix,
        'page_image': page_image,
    })
