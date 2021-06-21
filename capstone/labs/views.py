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
from capweb.templatetags.api_url import api_url

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

    first_year, last_year, case_stats, event_stats = get_timeline_stats(timeline.timeline)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'stats': [case_stats, event_stats],
        'first_year': first_year,
        'last_year': last_year,
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
                "description": "",
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

    # removing often-changing metadata fields from differ
    incoming_timeline.pop('first_year', None)
    incoming_timeline.pop('last_year', None)
    incoming_timeline.pop('stats', None)

    existing_timeline.pop('first_year', None)
    existing_timeline.pop('last_year', None)
    existing_timeline.pop('stats', None)

    # fixing a bug where an out-of-sync timeline in the user's browser clobbered an entire timeline.
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
    first_year, last_year, case_stats, event_stats = get_timeline_stats(timeline_record.timeline)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline_record.timeline,
        'stats': [case_stats, event_stats],
        'first_year': first_year,
        'last_year': last_year,
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


def h2o_import(request):
    # allowing users to import casebooks into chronolawgic
    h2o_domain = 'opencasebook.org'
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)
    data = json.loads(request.body.decode('utf-8'))
    use_original_urls = data['use_original_urls']

    h2o_url = data['url']
    parsed_url = urlparse(h2o_url)

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
            first_year, last_year, case_stats, event_stats = get_timeline_stats({'cases': timeline_cases, 'events': []})
            timeline = Timeline.objects.create(
                created_by=request.user,
                timeline=validate_and_normalize_timeline({
                    "title": "",
                    "author": "Imported from H2O",
                    "description": "Original H2O textbook can be found at this URL: " + original_casebook_url,
                    "stats": [case_stats, event_stats],
                    "first_year": first_year,
                    "last_year": last_year,
                    "cases": timeline_cases,
                    "events": [],
                    "categories": []
                })
            )
            timeline.save()
            return JsonResponse({'status': 'ok', 'timeline': timeline.timeline, 'id': timeline.uuid, 'missing_cases': missing_cases})
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


def get_timeline_stats(timeline):
    event_stats = []
    case_stats = []
    first_year = 9999999
    last_year = 0
    gathered_case_dates = {}
    gathered_event_dates = {}

    def get_year(datestring):
        return int(datestring.split('-')[0])

    for case in timeline['cases']:
        year = get_year(case['decision_date'])
        first_year = year if year < first_year else first_year
        last_year = year if year > last_year else last_year

        if year in gathered_case_dates:
            gathered_case_dates[year] += 1
        else:
            gathered_case_dates[year] = 1

    for event in timeline['events']:
        start_year = get_year(event['start_date'])
        end_year = get_year(event['end_date'])
        first_year = start_year if start_year < first_year else first_year
        last_year = end_year if end_year > last_year else last_year
        year = start_year
        while year < end_year + 1:
            if year in gathered_event_dates:
                gathered_event_dates[year] += 1
            else:
                gathered_event_dates[year] = 1
            year += 1

    year = first_year
    while year < last_year + 1:
        if year in gathered_case_dates:
            case_stats.append(gathered_case_dates[year])
        else:
            case_stats.append(0)
        if year in gathered_event_dates:
            event_stats.append(gathered_event_dates[year])
        else:
            event_stats.append(0)
        year += 1

    return first_year, last_year, case_stats, event_stats

# # # # END CHRONOLAWGIC # # # #
