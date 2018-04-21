from django.conf import settings
from django.shortcuts import render

from capapi import serializers
from capdb import models


def home(request):
    case = models.CaseMetadata.objects.get(id=settings.API_DOCS_CASE_ID)
    reporter = case.reporter
    reporter_metadata = serializers.ReporterSerializer(reporter, context={'request': request}).data
    case_metadata = serializers.CaseSerializer(case, context={'request': request}).data
    whitelisted_jurisdictions = models.Jurisdiction.objects.filter(whitelisted=True).values('name_long', 'name')

    return render(request, 'home.html', {
        "hide_footer": True,
        "case_metadata": case_metadata,
        "case_id": case_metadata['id'],
        "case_jurisdiction": case_metadata['jurisdiction'],
        "reporter_id": reporter_metadata['id'],
        "reporter_metadata": reporter_metadata,
        "whitelisted_jurisdictions": whitelisted_jurisdictions,
    })