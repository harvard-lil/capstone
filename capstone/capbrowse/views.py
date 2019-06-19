from django.shortcuts import render, get_object_or_404
from capdb.models import Jurisdiction, Court, Reporter
from collections import OrderedDict

from capweb.helpers import password_protected_page


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


@password_protected_page('ngrams')
def trends(request):
    q = request.GET.get('q')
    if q:
        title_suffix = ' for "%s"' % q
    else:
        title_suffix = ''
    return render(request, "trends.html", {
        'title': 'Historical Trends' + title_suffix,
        'page_image': None,
    })
