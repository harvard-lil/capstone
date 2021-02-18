import json

from django.shortcuts import render
from django.http import JsonResponse
from labs.models import Timeline
from datetime import date

from capweb.views import MarkdownView

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
        timelines = Timeline.objects.filter(created_by=request.user.pk)
        return JsonResponse({
            'status': 'ok',
            'timelines': [{"id": tl.id, "title": tl.timeline['title'], "subhead": tl.timeline['subhead']}
                           for tl in timelines],
        })

    if not timeline_id:
        return JsonResponse({'status': 'err', 'reason': 'forbidden'}, status=403)

    try:
        timeline = Timeline.objects.get(pk=timeline_id)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

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
        timeline = Timeline()
        timeline.created_by = request.user
        timeline.timeline = {
            "title": "Untitled Timeline",
            "subhead": "Created {}".format(date.today())
        }
        timeline.save()
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'status': 'ok',
        'timeline': timeline.timeline,
        'id': timeline.pk,
        'is_owner': True if request.user == timeline.created_by else False
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
        parsed = json.load(request.POST.get("timeline"))  # The JSON model field does not validate json
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

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    try:
        timeline = Timeline.objects.get(pk=timeline_id)
    except Timeline.DoesNotExist:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

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
