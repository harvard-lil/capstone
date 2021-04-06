import json
from dictdiffer import diff as dictdiff

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from labs.models import Timeline

from capweb.views import MarkdownView

from .helpers.chronolawgic import validate_timeline

# Labs-specific views
class LabMarkdownView(MarkdownView):
    # get labs branding in there
    pass


# # # # START CHRONOLAWGIC # # # #

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
                           "title": tl.timeline['title'] if 'title' in tl.timeline else "",
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
    timeline_record.timeline['description'] = incoming_timeline['description']
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
        timeline = Timeline.objects.create(created_by=request.user)
        timeline.timeline = {
            "title": "Untitled Timeline",
            "cases": [],
            "events": []
        }
        timeline.save()
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
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    if not request.user.is_authenticated or request.user != timeline_record.created_by:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        incoming_timeline = json.loads(request.body.decode())['timeline']  # The JSON model field does not validate json

    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    bad_values = validate_timeline(incoming_timeline)
    if bad_values:
        return JsonResponse(
            {'status': 'err',
             'reason': 'data_validation',
             'details': "Timeline Validation Errors: {}".format(bad_values)
             }, status=400)

    # fixing a bug where an out-of-sync timeine in the user's browser clobbered an entire timeline.
    number_of_items_modified = len(
        set(["{}{}".format(thing[1][0], thing[1][1]) for thing in dictdiff(timeline_record.timeline, incoming_timeline)
             if thing[0] != 'remove']
    ))

    number_of_items_removed = len([thing[0] for thing in dictdiff(timeline_record.timeline, incoming_timeline)
                             if thing[0] == 'remove'])

    if number_of_items_modified > 1 or number_of_items_removed > 1:
        return JsonResponse({'status': 'err', 'reason': "Timeline out of sync. More than one change or remove detected—"
                                                        " aborted change protect timeline. Please refresh "
                                                        "Chronolawgic. Did we mention this app is beta?😬"}, status=500)

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

# # # # END CHRONOLAWGIC # # # #
