import os
import json

from django.conf import settings
from django.shortcuts import render

from capdb import models, tasks


def jurisdiction_details(request, slug):
    try:
        jurisdiction = models.Jurisdiction.objects.get(slug=slug.lower())
    except models.Jurisdiction.DoesNotExist:
        jurisdiction = models.Jurisdiction.objects.order_by('slug').first()

    data_dir = settings.DATA_COUNT_DIR
    file_path = os.path.join(data_dir, "%s.json" % jurisdiction.id)

    if not os.path.exists(file_path):
        results = tasks.get_counts_for_jur(jurisdiction.id)
    else:
        with open(file_path, 'r') as f:
            results = json.load(f)

    jurisdictions = {}
    for jur in models.Jurisdiction.objects.all():
        jurisdictions[jur.id] = {
            'slug': jur.slug,
            'whitelisted': jur.whitelisted,
            'name_long': jur.name_long,
            'name': jur.name,
        }

    results['jurisdiction'] = jurisdiction

    return render(request, 'data/viz.html', {
        "hide_footer": True,
        'page_name': 'jurisdiction_details',
        'jurisdictions': jurisdictions,
        'data': results,
    })


def data_totals(request):
    jurisdictions = models.Jurisdiction.objects.all().order_by('name_long')
    data_dir = settings.DATA_COUNT_DIR

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

    return render(request, 'data/viz.html', {
        "hide_footer": True,
        'page_name': 'totals',
        'jurisdictions_for_handlebars': jurs,
        'jurisdictions': json.dumps(jurs),
        'data': json.dumps(case_count),
        # 'case_count_per_year': json.dumps(case_count_per_year)
        # 'count':
    })
