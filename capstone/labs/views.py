from django.shortcuts import render
from django.http import JsonResponse
from labs.models import TimeLine

from capweb.views import MarkdownView

# Labs-specific views
class LabMarkdownView(MarkdownView):
    # get labs branding in there
    pass


# # # # START CHRONOLAWGIC # # # #
#
#
#
# THESE ARE ALL UNTESTED BUT SHOULDN'T BE REACHABLE

def chronolawgic(request):
    return render(request, "lab/chronolawgic/timeline.html")


def chronolawgic_api_retrieve(request, timeline_id):
    if request.method != 'GET':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    timeline = TimeLine.objects.get(timeline_id)

    if not timeline:
        return JsonResponse({'status': 'err', 'reason': 'not_found'}, status=404)

    return JsonResponse({
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
        timeline = TimeLine()
        timeline.created_by = request.user
        timeline.timeline = {}
        timeline.save()
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'timeline': timeline.timeline,
        'id': timeline.pk,
        'is_owner': True if request.user == timeline.created_by else False
    })


def chronolawgic_api_update(request, timeline_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)

    timeline = TimeLine.objects.get(timeline_id)
    try:
        timeline.timeline = request.POST.get("timeline")
        timeline.save()
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'timeline': timeline.timeline,
        'id': timeline.pk,
        'is_owner': True if request.user == timeline.created_by else False
    })


def chronolawgic_api_delete(request, timeline_id):
    if request.method != 'DELETE':
        return JsonResponse({'status': 'err', 'reason': 'method_not_allowed'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'err', 'reason': 'auth'}, status=403)
    timeline = TimeLine.objects.get(timeline_id)
    try:
        timeline.delete()
    except Exception as e:
        return JsonResponse({'status': 'err', 'reason': e}, status=500)

    return JsonResponse({
        'timeline': timeline.timeline,
        'id': timeline.pk,
        'is_owner': True if request.user == timeline.created_by else False
    })

# # # # END CHRONOLAWGIC # # # #
