import json

from django.shortcuts import render
from django.http import JsonResponse
from labs.models import Timeline
from datetime import date

from capweb.views import MarkdownView

from .helpers.chronolawgic import validate_timeline

# Labs-specific views
class LabMarkdownView(MarkdownView):
    # get labs branding in there
    pass


# # # # START CHRONOLAWGIC # # # #

def chronolawgic(request):
    return render(request, "lab/chronolawgic/timeline.html")


def chronolawgic_api_retrieve(request, timeline_id=None):
    if request.method != 'GET':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    if not timeline_id and request.user.is_authenticated:
        timelines = Timeline.objects.filter(created_by=request.user.pk).order_by('id')
        return JsonResponse({
            'status': 'ok',
            'timelines': [{"id": tl.id,
                           "title": tl.timeline['title'] if 'title' in tl.timeline else "",
                           "subhead": tl.timeline['subhead'] if 'subhead' in tl.timeline else "",
                           "description": tl.timeline['description'] if 'description' in tl.timeline else "",
                           "case_count": len(tl.timeline['cases']) if 'cases' in tl.timeline else 0,
                           "event_count": len(tl.timeline['event']) if 'event' in tl.timeline else 0,
                           }
                           for tl in timelines],
        })

    if not timeline_id:
        return JsonResponse({'status': 'err', 'reason': 'forbidden'}, status=403)

    try:
        timeline = Timeline.objects.get(pk=timeline_id)
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
        'id': timeline.pk,
        'created_by': timeline.created_by.id,
        'is_owner': True if request.user == timeline.created_by else False
    })


def chronolawgic_api_update_admin(request, timeline_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline = Timeline.objects.get(pk=timeline_id)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)
    if not request.user.is_authenticated or timeline.created_by.pk != request.user.pk:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        timeline_content = json.loads(request.body.decode())
        timeline.timeline['title'] = timeline_content['title']
        timeline.timeline['subhead'] = timeline_content['subhead']
        timeline.timeline['description'] = timeline_content['description']
        timeline.save()
    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'id': timeline.pk,
        'is_owner': True if request.user == timeline.created_by else False
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
            "subhead": "Created {}".format(date.today()),
            "cases": [],
            "events": []
        }
        timeline.save()
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'id': timeline.pk,
        'is_owner': request.user == timeline.created_by
    })

def chronolawgic_api_update(request, timeline_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        timeline = Timeline.objects.get(pk=timeline_id)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    try:
        parsed = json.loads(request.body.decode())['timeline']  # The JSON model field does not validate json
        bad_values = validate_timeline(parsed)
        print(bad_values)
        if bad_values:
            return JsonResponse(
                {'status': 'err',
                 'reason': 'data_validation',
                 'details': "Timeline Validation Errors: {}".format(bad_values)
                 }, status=400)

        timeline.timeline = parsed
        timeline.save()
    except json.decoder.JSONDecodeError as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'id': timeline.pk,
        'is_owner': True if request.user == timeline.created_by else False
    })


def chronolawgic_api_delete(request, timeline_id):
    if request.method != 'DELETE':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    try:
        timeline = Timeline.objects.get(pk=timeline_id)
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
        'id': timeline.pk,
        'is_owner': True if request.user == timeline.created_by else False
    })

# # # # END CHRONOLAWGIC # # # #
