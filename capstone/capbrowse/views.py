from django.shortcuts import render
from django.http import JsonResponse
from capdb.models import Jurisdiction, Court, Reporter
from collections import OrderedDict

# Create your views here.

def view_case(request, case_id):
    return render(request, "view_case.html", {'case_id':case_id})

def view_jurisdiction(request, jurisdiction_id):
    jurisdiction = Jurisdiction.objects.get(pk=jurisdiction_id)
    fields = _get_fields(jurisdiction)
    return render(request, "view_metadata.html", {
        'fields': fields,
        'type': 'court',
        'title': jurisdiction.name
    })

def view_reporter(request, reporter_id):
    reporter = Reporter.objects.get(pk=reporter_id)
    fields = _get_fields(reporter)
    return render(request, "view_metadata.html", {
        'fields': fields,
        'type': 'reporter',
        'title': reporter.short_name
    })

def view_court(request, court_id):
    court = Court.objects.get(pk=court_id)
    fields = _get_fields(court)

    return render(request, "view_metadata.html", {
        'fields': fields,
        'type': 'court',
        'title': court.name_abbreviation
    })

def search(request):
    return render(request, "search.html")

def _get_fields(object):
    fields = OrderedDict()
    for field in object._meta.get_fields():
        print(field.name, field.get_internal_type())
        if field.get_internal_type() == "ManyToManyField" or field.get_internal_type() == "ForeignKey":
            continue
        try:
            fields[field.name.replace("_", " ").title()] = getattr(object, field.name)
        except AttributeError as e:
            print(e)
    return fields