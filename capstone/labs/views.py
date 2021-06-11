import json
import os
import requests
import uuid
from dictdiffer import diff as dictdiff
from multiprocessing.pool import ThreadPool
from urllib.parse import urlparse

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from labs.models import Timeline

from capweb.views import MarkdownView

from .helpers.chronolawgic import validate_and_normalize_timeline, TimelineValidationException


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
        timeline = Timeline.objects.get(uuid=timeline_uuid)
        if 'cases' not in timeline.timeline:
            timeline.timeline['cases'] = []
        if 'events' not in timeline.timeline:
            timeline.timeline['events'] = []
        timeline.save()

    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'id': timeline.uuid,
        'created_by': timeline.created_by.id,
        'is_owner': True if request.user == timeline.created_by else False
    })


def chronolawgic_api_update_admin(request, timeline_uuid):
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
    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    timeline_record.timeline['title'] = incoming_timeline['title']
    timeline_record.timeline['author'] = incoming_timeline['author'] if 'author' in incoming_timeline else None
    timeline_record.timeline['description'] = incoming_timeline['description']

    try:
        timeline_record.timeline = validate_and_normalize_timeline(timeline_record.timeline)
    except TimelineValidationException as e:
        return JsonResponse(
            {'status': 'err',
             'reason': 'data_validation',
             'details': "Timeline Validation Errors: {}".format(e)
             }, status=400)

    timeline_record.save()

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline_record.timeline,
        'id': timeline_record.uuid,
        'is_owner': True if request.user == timeline_record.created_by else False
    })


def chronolawgic_api_create(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        timeline = Timeline.objects.create(
            created_by=request.user,
            timeline=validate_and_normalize_timeline({
                "title": "",
                "author": "",
                "cases": [],
                "events": [],
                "categories": []
            })
        )
        timeline.save()
    except TimelineValidationException as e:
        return JsonResponse(
            {'status': 'err',
             'reason': 'data_validation',
             'details': "Problem creating timeline— update internal template {}".format(e)
             }, status=400)
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'id': timeline.uuid,
        'is_owner': request.user == timeline.created_by
    })


def chronolawgic_api_update(request, timeline_uuid):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline_record = Timeline.objects.get(uuid=timeline_uuid)
        existing_timeline = timeline_record.timeline
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    if not request.user.is_authenticated or request.user != timeline_record.created_by:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        incoming_timeline = json.loads(request.body.decode())['timeline']  # The JSON model field does not validate json

    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    try:
        incoming_timeline = validate_and_normalize_timeline(incoming_timeline)
        existing_timeline = validate_and_normalize_timeline(existing_timeline)
    except TimelineValidationException as e:
        return JsonResponse(
            {'status': 'err',
             'reason': 'data_validation',
             'details': "Timeline Validation Errors: {}".format(e)
             }, status=400)

    # fixing a bug where an out-of-sync timeine in the user's browser clobbered an entire timeline.
    number_of_items_modified = len(
        set(["{}{}".format(thing[1][0], thing[1][1]) for thing in dictdiff(existing_timeline, incoming_timeline)
             if thing[0] != 'remove']
            ))

    number_of_items_removed = len([thing[0] for thing in dictdiff(existing_timeline, incoming_timeline)
                                   if thing[0] == 'remove'])

    if number_of_items_modified > 1 or number_of_items_removed > 1:
        return JsonResponse({'status': 'err', 'reason': "Timeline out of sync. More than one change or remove detected—"
                                                        " aborted change protect timeline. Please refresh "
                                                        "Chronolawgic. Did we mention this app is beta?😬 {}".format(
            [thing for thing in dictdiff(existing_timeline, incoming_timeline)])}, status=500)

    timeline_record.timeline = incoming_timeline
    timeline_record.save()

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline_record.timeline,
        'id': timeline_record.uuid,
        'is_owner': True if request.user == timeline_record.created_by else False
    })


def chronolawgic_api_delete(request, timeline_uuid):
    if request.method != 'DELETE':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline = Timeline.objects.get(uuid=timeline_uuid)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    if not request.user.is_authenticated or timeline.created_by.pk != request.user.pk:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        timeline.delete()
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'id': timeline.uuid,
        'is_owner': True if request.user == timeline.created_by else False
    })

def get_case(case):
    api_url = "https://api.case.law/v1/cases/?cite=%s" % case['citations'][0]
    case_found = requests.get(api_url)
    if case_found.status_code == 200:
        case_json = case_found.json()['results']
        if len(case_json):
            return {
                "id": str(uuid.uuid4()),
                "url": case_json[0]["url"],
                "citation": case,
                "name": case_json[0]["name_abbreviation"],
                "decision_date": case_json[0]["decision_date"],
                "jurisdiction": case_json[0]["jurisdiction"]["name_long"],
                "court": case_json[0]["court"]["name"]
            }
        else:
            return case

def h2o_import(request):
    h2o_domain = 'opencasebook.org'
    import time
    print('START', time.ctime())
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)
    h2o_url = json.loads(request.body.decode('utf-8'))['url']
    parsed_url = urlparse(h2o_url)

    if parsed_url.netloc != h2o_domain:
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=403)

    h2o_url = os.path.join('https://' + h2o_domain + parsed_url.path.replace('casebooks', 'casebook'), 'toc')

    try:
        resp = requests.get(h2o_url)
        if resp.status_code == 200:
            casebook = resp.json()
            cases = get_citation(casebook, [])

            pool = ThreadPool(20)
            mapper = pool.map

            def file_map(func, files, *args, **kwargs):
                return list(mapper((lambda f: func(f)), files))

            possible_cases = file_map(get_case, cases)
            missing_cases = []
            timeline_cases = []
            for case in possible_cases:
                if 'id' in case:
                    timeline_cases.append(case)
                else:
                    missing_cases.append(case)

            timeline = Timeline.objects.create(
                created_by=request.user,
                timeline=validate_and_normalize_timeline({
                    "title": "",
                    "author": "",
                    "cases": timeline_cases,
                    "events": [],
                    "categories": []
                })
            )
            timeline.save()
            print('AAAANnnndd were DONE',  time.ctime())
            return JsonResponse({'status': 'ok', 'timeline': timeline.timeline,'missing_cases': missing_cases})
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
                        'citations': citations}
                    cases.append(found_case)
            if 'children' in case:
                get_citation(case, cases)
    return cases


# # # # END CHRONOLAWGIC # # # #
