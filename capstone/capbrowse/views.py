from django.shortcuts import render
from django.http import JsonResponse
from capdb.models import Jurisdiction, Court, Reporter

# Create your views here.

def browse_case(request, case_id):
    return render(request, "browse_case.html", {'case_id':case_id})

def browse(request):
    return render(request, "browse.html")

def jurisdiction_list(request):
    return JsonResponse({ jurisdiction.slug: jurisdiction.name_long for jurisdiction in Jurisdiction.objects.all() if jurisdiction.slug != 'regional' and jurisdiction.slug != 'tribal' })

def court_list(request):
    return JsonResponse({ court.slug: "{}: {}".format(court.jurisdiction, court.name) for court in Court.objects.all() })

def reporter_list(request):
    return JsonResponse({ reporter.id: "{}- {}".format(reporter.short_name, reporter.full_name) for reporter in Reporter.objects.all() })
