import os
import json
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


def data(request):
    jurisdictions = models.Jurisdiction.objects.all().order_by('name_long')
    data_dir = 'capapi/data/'

    with open(os.path.join(data_dir, 'court_count.json'), 'r') as f:
        court_count = json.load(f)

    with open(os.path.join(data_dir, 'reporter_count.json'), 'r') as f:
        reporter_count = json.load(f)

    with open(os.path.join(data_dir, 'case_count.json'), 'r') as f:
        case_count = json.load(f)

    jurs = {}

    for jur in jurisdictions:
        jurs[jur.id] = {
            'slug': jur.slug,
            'whitelisted': jur.whitelisted,
            'name_long': jur.name_long,
            'name': jur.name,
        }

    return render(request, 'data-viz.html', {
            'jurisdictions': jurs,
            'jurisdiction_data': json.dumps(jurs),
            'court_count': json.dumps(court_count),
            'reporter_count': json.dumps(reporter_count),
            'case_count': json.dumps(case_count)
    })
