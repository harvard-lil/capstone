import os
import json
from collections import OrderedDict

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from capdb import models, tasks


def details_view(request):
    jurisdictions = {}
    for jur in models.Jurisdiction.objects.all():
        jurisdictions[jur.id] = {
            'slug': jur.slug,
            'whitelisted': jur.whitelisted,
            'name_long': jur.name_long,
            'name': jur.name,
        }

    # order by full name of jurisdiction
    jurisdictions = OrderedDict(sorted(jurisdictions.items(), key=lambda t: t[1]['name_long']))
    return render(request, 'data/viz-details.html', {
        "hide_footer": True,
        'jurisdictions': jurisdictions,
    })


def totals_view(request):
    jurisdictions = models.Jurisdiction.objects.all()
    data_dir = settings.DATA_COUNT_DIR

    with open(os.path.join(data_dir, 'totals.json'), 'r') as f:
        case_count = json.load(f)

    jurs = {}

    for jur in jurisdictions:
        jurs[jur.id] = {
            'slug': jur.slug,
            'whitelisted': jur.whitelisted,
            'name_long': jur.name_long,
            'name': jur.name,
        }

    # order by full name of jurisdiction
    jurs = OrderedDict(sorted(jurs.items(), key=lambda t: t[1]['name_long']))
    return render(request, 'data/viz-totals.html', {
        "hide_footer": True,
        'jurisdictions': json.dumps(jurs),
        'data': json.dumps(case_count),
    })


def get_details(request, slug=None):
    if not slug:
        return JsonResponse({})
    try:
        jurisdiction = models.Jurisdiction.objects.get(slug=slug)
    except models.Jurisdiction.DoesNotExist:
        jurisdiction = models.Jurisdiction.objects.first()

    data_dir = settings.DATA_COUNT_DIR
    file_path = os.path.join(data_dir, "%s.json" % jurisdiction.id)

    if not os.path.exists(file_path):
        results = {
            'case_count': tasks.get_case_count_for_jur(jurisdiction.id),
            'reporter_count': tasks.get_reporter_count_for_jur(jurisdiction.id),
            'court_count': tasks.get_court_count_for_jur(jurisdiction.id),
        }

    else:
        with open(file_path, 'r') as f:
            results = json.load(f)
    results['jurisdiction'] = {
        'slug': jurisdiction.slug,
        'id': jurisdiction.id,
        'name_long': jurisdiction.name_long,
        'whitelisted': jurisdiction.whitelisted
    }

    return JsonResponse(results)
