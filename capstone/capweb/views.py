from collections import OrderedDict

from django.shortcuts import render
from django.conf import settings

from capweb.forms import ContactForm
from capweb.helpers import get_data_from_lil_site
from capweb.resources import send_contact

def index(request):
    news = get_data_from_lil_site(section="news")
    numbers = {
        "pages_scanned": 40,
        "cases": 6.4,
        "reporters": 627,
    }
    return render(request, "index.html", {
        'page_name': 'index',
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
    if request.method == 'GET':
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['sender'] = request.user.email
        form = ContactForm(initial=initial_data)
        return render(request, "contact.html", {
            "page_name": "contact",
            "form": form,
            "email": settings.EMAIL_ADDRESS,
        })

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            send_contact(form.data)
            return render(request, "contact_success.html", {
                "page_name": "contact",
            })


def tools(request):
    return render(request, "tools.html", {"page_name": "tools"})


def gallery(request):
    return render(request, "gallery.html", {"page_name": "gallery"})


def wordclouds(request):
    return render(request, "gallery/wordclouds.html", {"page_name": "wordclouds"})


def limericks(request):
    return render(request, "gallery/limericks.html", {"page_name": "limericks"})