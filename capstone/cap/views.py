from django.http import HttpResponse
from django.shortcuts import render

from .models import Reporter, VolumeMetadata, VolumeXML, CaseXML, PageXML


def index(request):
    counts = {model_name: globals()[model_name].objects.count() for model_name in ('Reporter', 'VolumeMetadata', 'VolumeXML', 'CaseXML', 'PageXML')}
    return render(request, "index.html", {
        'counts': counts,
    })