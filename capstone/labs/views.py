import json
import os
import requests
import uuid

from multiprocessing.pool import ThreadPool
from urllib.parse import urlparse

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from labs.models import Timeline, TimelineValidationException

from capweb.views import MarkdownView
from capweb.templatetags.api_url import api_url


# Labs-specific views
class LabMarkdownView(MarkdownView):
    # get labs branding in there
    pass


# # # # START CHRONOLAWGIC # # # #

def chronolawgic_redirect(request):
    return redirect('labs:chronolawgic-dashboard')


def chronolawgic(request, timeline_uuid=None):
    return render(request, "lab/chronolawgic/timeline.html")


@never_cache
def chronolawgic_api_retrieve(request, timeline_uuid=None):
    if request.method != 'GET':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    if not timeline_uuid and request.user.is_authenticated:
        timelines = Timeline.objects.filter(created_by=request.user.pk).order_by('-id')
        return JsonResponse({
            'status': 'ok',
            'timelines': [{"id": tl.uuid,
                           "title": tl.timeline['title'] if 'title' in tl.timeline else "(untitled)",
                           "author": tl.timeline['author'] if 'author' in tl.timeline else None,
                           "description": tl.timeline['description'] if 'description' in tl.timeline else "",
                           "case_count": len(tl.timeline['cases']) if 'cases' in tl.timeline else 0,
                           "event_count": len(tl.timeline['events']) if 'events' in tl.timeline else 0,
                           }
                          for tl in timelines],
        })

    if not timeline_uuid:
        return JsonResponse({
            'status': 'ok',
            'timelines': []})
    try:
        timeline_record = Timeline.objects.get(uuid=timeline_uuid)

    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    case_years = timeline_record.case_years()
    event_years = timeline_record.event_years()

    first_year = Timeline.first_year(case_years, event_years)
    last_year = Timeline.last_year(case_years, event_years)
    event_stats = Timeline.event_stats(event_years, first_year, last_year)
    case_stats = Timeline.case_stats(case_years, first_year, last_year)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline_record.timeline,
        'stats': [case_stats, event_stats],
        'first_year': first_year,
        'last_year': last_year,
        'id': timeline_record.uuid,
        'created_by': timeline_record.created_by.id,
        'is_owner': True if request.user == timeline_record.created_by else False
    })


def chronolawgic_update_timeline_metadata(request, timeline_uuid):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline_record = Timeline.objects.get(uuid=timeline_uuid)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)
    if not request.user.is_authenticated or timeline_record.created_by.pk != request.user.pk:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        incoming_timeline = json.loads(request.body.decode())
        timeline_record.update_timeline_metadata(incoming_timeline)
    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)
    except TimelineValidationException as e:
        return JsonResponse(
            {'status': 'err',
             'reason': 'data_validation',
             'details': "Timeline Validation Errors: {}".format(e)
             }, status=400)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline_record.timeline
    })


def chronolawgic_api_create(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    timeline_record = Timeline(
        timeline=Timeline.generate_empty_timeline(),
        created_by=request.user
    )
    timeline_record.save()

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline_record.timeline,
        'id': timeline_record.uuid,
        'is_owner': request.user == timeline_record.created_by
    })


def chronolawgic_update_categories(request, timeline_uuid):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline_record = Timeline.objects.get(uuid=timeline_uuid)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'timeline_not_found'}, status=404)

    if not request.user.is_authenticated or request.user != timeline_record.created_by:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        categories = [Timeline.normalize_and_validate_single_object('categories', category) for category in
                      json.loads(request.body.decode())]
        timeline_record.timeline['categories'] = categories
        timeline_record.save()
    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)
    except TimelineValidationException as e:
        return JsonResponse(
            {'status': 'err',
             'reason': 'data_validation',
             'details': str(e)
             }, status=400)

    return JsonResponse({
        'status': 'ok',
        'message': 'updated categories',
        'timeline': timeline_record.timeline
    })


def chronolawgic_add_update_subobject(request, subobject_type, timeline_uuid):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline_record = Timeline.objects.get(uuid=timeline_uuid)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'timeline_not_found'}, status=404)

    if not request.user.is_authenticated or request.user != timeline_record.created_by:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        subobject = Timeline.normalize_and_validate_single_object(subobject_type, json.loads(request.body.decode()))
        timeline_record.add_update_subobject(subobject, subobject_type)
    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)
    except TimelineValidationException as e:
        return JsonResponse(
            {'status': 'err',
             'reason': 'data_validation',
             'details': str(e)
             }, status=400)

    case_years = timeline_record.case_years()
    event_years = timeline_record.event_years()

    first_year = Timeline.first_year(case_years, event_years)
    last_year = Timeline.last_year(case_years, event_years)
    event_stats = Timeline.event_stats(event_years, first_year, last_year)
    case_stats = Timeline.case_stats(case_years, first_year, last_year)

    return JsonResponse({
        'status': 'ok',
        'message': 'updated {} list'.format(subobject_type),
        'timeline': timeline_record.timeline,
        'stats': [case_stats, event_stats],
        'first_year': first_year,
        'last_year': last_year,
    })


def chronolawgic_delete_subobject(request, timeline_uuid, subobject_type, subobject_uuid):
    if request.method != 'DELETE':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)
    try:
        timeline_record = Timeline.objects.get(uuid=timeline_uuid)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'timeline_not_found'}, status=404)

    if not request.user.is_authenticated or request.user != timeline_record.created_by:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    timeline_record.delete_subobject(subobject_type, subobject_uuid)

    case_years = timeline_record.case_years()
    event_years = timeline_record.event_years()

    first_year = Timeline.first_year(case_years, event_years)
    last_year = Timeline.last_year(case_years, event_years)
    event_stats = Timeline.event_stats(event_years, first_year, last_year)
    case_stats = Timeline.case_stats(case_years, first_year, last_year)

    return JsonResponse({
        'status': 'ok',
        'message': 'deleted {}'.format(subobject_type),
        'timeline': timeline_record.timeline,
        'stats': [case_stats, event_stats],
        'first_year': first_year,
        'last_year': last_year,
    })


def chronolawgic_api_delete(request, timeline_uuid):
    if request.method != 'DELETE':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline_record = Timeline.objects.get(uuid=timeline_uuid)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    if not request.user.is_authenticated or timeline_record.created_by.pk != request.user.pk:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        timeline_record.delete()
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'status': 'ok',
        'id': timeline_uuid,
    })


def h2o_import(request):
    # allowing users to import casebooks into chronolawgic
    h2o_domain = 'opencasebook.org'
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)
    data = json.loads(request.body.decode('utf-8'))
    use_original_urls = data['use_original_urls']

    h2o_url = data['url']
    parsed_url = urlparse(h2o_url)

    if not parsed_url:
        return JsonResponse({'status': 'err', 'reason': 'no_h2o_url'}, status=403)

    # expecting an H2O URL, no shenanigans
    if parsed_url.netloc != h2o_domain:
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=403)

    # getting casebook's H2O API URL
    h2o_url = os.path.join('https://' + h2o_domain + parsed_url.path.replace('casebooks', 'casebook'), 'toc')
    original_casebook_url = os.path.join('https://' + h2o_domain + parsed_url.path.replace('casebook/', 'casebooks/'))

    try:
        resp = requests.get(h2o_url)
        if resp.status_code == 200:
            casebook = resp.json()
            cases = get_citation(casebook, [])

            pool = ThreadPool(20)
            mapper = pool.map
            possible_cases = list(mapper((lambda f: get_case(f, use_original_urls)), cases))

            missing_cases = []
            timeline_cases = []

            for case in possible_cases:
                if 'id' in case:
                    timeline_cases.append(case)
                else:
                    missing_cases.append(case)

            timeline_record = Timeline(
                timeline=Timeline.generate_empty_timeline(
                    {"author": "(Imported from H2O)",
                     "description": "Original H2O textbook can be found at this URL: " + original_casebook_url,
                     "cases": timeline_cases}
                ),
                created_by=request.user,
            )
            timeline_record.save()

            # case_years and event_years must be generated after there are cases in the TL
            case_years = timeline_record.case_years()
            event_years = timeline_record.event_years()

            first_year = Timeline.first_year(case_years, event_years)
            last_year = Timeline.last_year(case_years, event_years)
            case_stats = Timeline.case_stats(case_years, first_year, last_year)
            event_stats = Timeline.event_stats(event_years, first_year, last_year)

            # no need to save these changes, just return them
            timeline_record.timeline['first_year'] = Timeline.first_year(case_years, event_years)
            timeline_record.timeline['last_year'] = Timeline.last_year(case_years, event_years)
            timeline_record.timeline['stats'] = [case_stats, event_stats]

            return JsonResponse({'status': 'ok', 'timeline': timeline_record.timeline, 'id': timeline_record.uuid,
                                 'missing_cases': missing_cases})
        else:
            return JsonResponse({'status': 'err', 'reason': ''}, status=resp.status_code)
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=404)


def get_citation(obj, cases=None):
    # it's possible for h2o cases to be nested so we're
    # calling this recursively, creating a flat list
    if cases is None:
        cases = []

    if 'children' in obj:
        for case in obj['children']:
            if case['resource_type'] == 'Case' and case['citation']:
                if case['citation']:
                    citations = case['citation'].split(', ') if 'citation' in case else []
                    found_case = {
                        'name': case['title'],
                        'citations': citations,
                        'original_url': case['url']}
                    cases.append(found_case)
            if 'children' in case:
                get_citation(case, cases)
    return cases


def get_case(case, use_original_urls=False):
    # getting cases from CAP because we need to find dates
    capapi_url = api_url('cases-list') + "?cite=%s" % case['citations'][0]
    case_found = requests.get(capapi_url)
    if case_found.status_code == 200:
        case_json = case_found.json()['results']
        if len(case_json):
            return {
                "id": str(uuid.uuid4()),
                "url": 'https://opencasebook.org' + case['original_url'] if use_original_urls else case_json[0]["url"],
                "citation": case['citations'][0],
                "name": case_json[0]["name_abbreviation"],
                "decision_date": case_json[0]["decision_date"],
                "jurisdiction": case_json[0]["jurisdiction"]["name_long"],
                "court": case_json[0]["court"]["name"]
            }
        else:
            # didn't find case, returning H2O case object for
            # error reporting on the frontend
            return case


def legacy_please_refresh(request, timeline_uuid):
    return JsonResponse({
        'status': 'err',
        'reason': 'legacy_api_call',
        'details': "Command Failed: Refresh Page: {}".format(timeline_uuid),
        "uuid": timeline_uuid
    }, status=400)

# # # # END CHRONOLAWGIC # # # #
