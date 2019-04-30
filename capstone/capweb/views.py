import logging
import os
from collections import OrderedDict

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.views import View

from capweb.forms import ContactForm
from capweb.helpers import get_data_from_lil_site, reverse, send_contact_email, render_markdown

from capdb.models import CaseMetadata, Jurisdiction, Reporter, Snippet
from capapi import serializers
from capapi.resources import form_for_request

logger = logging.getLogger(__name__)


def index(request):
    news = get_data_from_lil_site(section="news")
    federal = {
        "cases": 1693904,
        "reporters": 32,
        "pages_scanned": 9547364,
    }

    state = {
        "cases": 6.7,
        "reporters": 627,
        "pages_scanned": 40,
    }

    return render(request, "index.html", {
        'news': news[0:5],
        'state': state,
        'federal': federal,
        'page_image': 'img/og_image/index.png',
        'page_name': 'home'
    })


def about(request):
    news = get_data_from_lil_site(section="news")
    contributors = get_data_from_lil_site(section="contributors")
    sorted_contributors = {}
    for contributor in contributors:

        sorted_contributors[contributor['sort_name']] = contributor
        if contributor['affiliated']:
            sorted_contributors[contributor['sort_name']]['hash'] = contributor['name'].replace(' ', '-').lower()
    sorted_contributors = OrderedDict(sorted(sorted_contributors.items()), key=lambda t: t[0])
    return render(request, "about.html", {
        "page_name": "about",
        "contributors": sorted_contributors,
        "news": news,
        "email": settings.DEFAULT_FROM_EMAIL,
        'page_image': 'img/og_image/about.png',
        'page_title': 'About the Caselaw Access Project',
        'page_description': 'The Caselaw Access Project (“CAP”) expands public access to U.S. law. Our goal is to make'
                            'all published U.S. court decisions freely available to the public online, in a consistent '
                            'format, digitized from the collection of the Harvard Law Library.',
    })


def contact(request):
    form = form_for_request(request, ContactForm)

    if request.method == 'POST' and form.is_valid():
        data = form.data
        send_contact_email(data.get('subject'), data.get('message'), data.get('email'))
        logger.info("sent contact email: %s" % data)
        return HttpResponseRedirect(reverse('contact-success'))

    email_from = request.user.email if request.user.is_authenticated else ""
    form.initial = {"email": email_from}

    return render(request, 'contact.html', {
        "form": form,
        "email": settings.DEFAULT_FROM_EMAIL,
        'page_image': 'img/og_image/contact.png',
        'page_title': 'Contact Caselaw Access Project',
        'page_description': 'Email us at %s or fill out this form. ' % settings.DEFAULT_FROM_EMAIL,
    })


def tools(request):
    return render(request, 'tools.html', {
        'page_image': 'img/og_image/tools.png',
        'page_title': 'Caselaw Access Project Tools',
        'page_description': 'The capstone of the Caselaw Access Project is a robust set of tools which facilitate access'
                            ' to the cases and their associated metadata. We currently offer two ways to access the '
                            'data: our API, and bulk downloads.'
    })


def gallery(request):
    return render(request, 'gallery.html', {
        'email': settings.DEFAULT_FROM_EMAIL,
        'page_image': 'img/og_image/gallery.png',
        'page_title': 'Caselaw Access Project Project Gallery',
        'page_description': 'Sky is the limit! Here are some examples of what’s possible.'
    })


def maintenance_mode(request):
    return render(request, "error_page.html", {
        "type": "Maintenance",
        "title": "${title}",
        "middle": "${middle}",
        "bottom": "${bottom}",
        "action": "${action}",
        'page_image': 'img/og_image/api.png',
        'page_title': 'Caselaw Access Project: Error',
        'page_description': 'This page is broken. Let us know if this should be working.'
    })


def wordclouds(request):
    wordcloud_dir = os.path.join(settings.BASE_DIR, 'static/img/wordclouds')
    wordclouds = [w for w in os.listdir(wordcloud_dir) if w.endswith('.png')]
    return render(request, "gallery/wordclouds.html", {
        "wordclouds": wordclouds,
        'page_image': 'img/og_image/wordclouds.png',
        'page_title': 'Caselaw Access Project Project California Wordclouds',
        'page_description': 'Most used words in California caselaw from 1853 to 2015'
    })


def limericks(request):
    return render(request, 'gallery/limericks.html', {
        'page_image': 'img/og_image/limericks.png',
        'page_title': 'Caselaw Access Project Project Limericks!',
        'page_description': 'Generate rhymes using caselaw!'
    })


def api(request):
    # TODO: Trim what we don't need here
    try:
        case = CaseMetadata.objects.get(id=settings.API_DOCS_CASE_ID)
    except CaseMetadata.DoesNotExist:
        case = CaseMetadata.objects.filter(duplicative=False).first()
    reporter = Reporter.objects.first()
    reporter_metadata = serializers.ReporterSerializer(reporter, context={'request': request}).data
    case_metadata = serializers.CaseSerializer(case, context={'request': request}).data
    whitelisted_jurisdictions = Jurisdiction.objects.filter(whitelisted=True).values('name_long', 'name')

    return render(request, 'api.html', {
        "page_name": True,
        "case_metadata": case_metadata,
        "case_id": case_metadata['id'],
        "case_jurisdiction": case_metadata['jurisdiction'],
        "reporter_id": reporter_metadata['id'],
        "reporter_metadata": reporter_metadata,
        "whitelisted_jurisdictions": whitelisted_jurisdictions,
        'page_image': 'img/og_image/tools_api.png',
        'page_title': 'Caselaw Access Project API Documentation',
        'page_description': 'To get started with the API, you can explore it in your browser, or reach it from the '
                            'command line.'
    })


def search_docs(request):
    return render(request, 'search_docs.html')


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
            **self.extra_context,
            **meta,
        })