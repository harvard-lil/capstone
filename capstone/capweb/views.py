from collections import OrderedDict
from django.shortcuts import render

from capweb.helpers import get_data_from_lil_site


def index(request):
    news = get_data_from_lil_site(section="news")
    numbers = {
        "pages_scanned": "40M",
        "cases": "6.4M",
        "reporters": "627",
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
    sorted_contributors = OrderedDict(sorted(sorted_contributors.items()), key=lambda t: t[0])
    return render(request, "about.html", {
        "page_name": "about",
        "contributors": sorted_contributors,
        "news": news
    })


def tools(request):
    return render(request, "tools.html", {"page_name": "tools"})
