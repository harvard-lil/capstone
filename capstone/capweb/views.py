import os
from collections import OrderedDict

from django.shortcuts import render
from django.conf import settings

from capweb.forms import ContactForm
from capweb.helpers import get_data_from_lil_site

from capdb.models import CaseMetadata, Jurisdiction
from capapi import serializers
from capapi.resources import form_for_request

from capweb.resources import send_contact


def index(request):
    news = get_data_from_lil_site(section="news")
    numbers = {
        "pages_scanned": 40,
        "cases": 6.4,
        "reporters": 627,
    }
    return render(request, "index.html", {
        'news': news[0:5],
        'numbers': numbers,
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
        "news": news
    })


def contact(request):
    form = form_for_request(request, ContactForm)

    if request.method == 'POST' and form.is_valid():
        send_contact(form.data)
        return render(request, "contact_success.html")

    if request.user.is_authenticated:
        form = ContactForm(initial={'email': request.user.email})

    return render(request, 'contact.html', {"form": form})


def tools(request):
    return render(request, "tools.html")


def gallery(request):
    return render(request, "gallery.html")


def wordclouds(request):
    wordcloud_dir = os.path.join(settings.BASE_DIR, 'static/img/wordclouds')
    wordclouds = [w for w in os.listdir(wordcloud_dir) if w.endswith('.png')]
    return render(request, "gallery/wordclouds.html", {
        "wordclouds": wordclouds,
    })


def limericks(request):
    return render(request, "gallery/limericks.html")


def api(request):
    #TODO: Trim what we don't need here
    try:
        case = CaseMetadata.objects.get(id=settings.API_DOCS_CASE_ID)
    except CaseMetadata.DoesNotExist:
        case = CaseMetadata.objects.filter(duplicative=False).first()
    reporter = case.reporter
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
    })
