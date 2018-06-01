import os
import json

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from capdb import models, tasks


def details_view(request):
    # if we're receiving an ajax request for a certain slug,
    # send back JSON data for particular slug
    if request.is_ajax() and request.GET.get('slug', None):
        try:
            jurisdiction = models.Jurisdiction.objects.get(slug=request.GET.get('slug'))
        except models.Jurisdiction.DoesNotExist:
            jurisdiction = models.Jurisdiction.objects.order_by('slug').first()
        data_dir = settings.DATA_COUNT_DIR
        file_path = os.path.join(data_dir, "%s.json" % jurisdiction.id)

        if not os.path.exists(file_path):
            results = {
                'case_count': tasks.get_case_count_for_jur(jur),
                'reporter_count': tasks.get_reporter_count_for_jur(jur),
                'court_count': tasks.get_court_count_for_jur(jur),
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

    # otherwise send back template with jurisdiction data
    jurisdictions = {}
    for jur in models.Jurisdiction.objects.all():
        jurisdictions[jur.id] = {
            'slug': jur.slug,
            'whitelisted': jur.whitelisted,
            'name_long': jur.name_long,
            'name': jur.name,
        }

    return render(request, 'data/viz-details.html', {
        "hide_footer": True,
        'page_name': 'jurisdiction_details',
        'jurisdictions': jurisdictions,
    })


def totals_view(request):
    jurisdictions = models.Jurisdiction.objects.all().order_by('name_long')
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

    return render(request, 'data/viz-totals.html', {
        "hide_footer": True,
        'page_name': 'totals',
        'jurisdictions': json.dumps(jurs),
        'data': json.dumps(case_count),
    })
