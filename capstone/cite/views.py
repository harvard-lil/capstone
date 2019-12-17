import re
import time
from collections import defaultdict
from contextlib import contextmanager
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.db.models import Q, Prefetch
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.text import slugify
from rest_framework.request import Request
from elasticsearch.exceptions import NotFoundError

from capapi import serializers
from capapi.documents import CaseDocument
from capapi.authentication import SessionAuthentication
from capapi.renderers import HTMLRenderer
from capdb.models import Reporter, VolumeMetadata, CaseMetadata
from capweb import helpers

### helpers ###
from capweb.helpers import natural_sort_key

def safe_redirect(request):
    """ Redirect to request.GET['next'] if it exists and is safe, or else to '/' """
    next = request.POST.get('next') or request.GET.get('next') or '/'
    return HttpResponseRedirect(next if is_safe_url(next, allowed_hosts={request.get_host()}) else '/')

@contextmanager
def locked_session(request, using='default'):
    """
        Reload the user session for exclusive access.
        This is based on django.contrib.sessions.backends.db.SessionStore.load(), and assumes that we are using the
        db session store.
    """
    with transaction.atomic(using=using):
        session = request.session
        try:
            s = session.model.objects.select_for_update().get(session_key=session.session_key, expire_date__gt=timezone.now())
            temp_session = session.decode(s.session_data)
        except (session.model.DoesNotExist, SuspiciousOperation) as e:
            temp_session = {}
        try:
            yield temp_session
        finally:
            request.session.update(temp_session)
            request.session.save()


### views ###

def home(request):
    """ Base page -- list all of our jurisdictions and reporters. """

    # get reporters sorted by jurisdiction
    reporters = Reporter.objects.filter(is_nominative=False).exclude(start_year=None).prefetch_related('jurisdictions').order_by('short_name')
    reporters_by_jurisdiction = defaultdict(list)
    for reporter in reporters:
        for jurisdiction in reporter.jurisdictions.all():
            reporters_by_jurisdiction[jurisdiction].append(reporter)

    # prepare (jurisdiction, reporters) list
    jurisdictions = sorted(reporters_by_jurisdiction.items(), key=lambda item: item[0].name_long)

    return render(request, 'cite/home.html', {
        "jurisdictions": jurisdictions,
    })

def robots(request):
    """
        Disallow all URLs with no_index=True and robots_txt_until >= now.
    """
    return HttpResponse("\n".join(
        ["user-agent: *"]+
        ["disallow: %s" % c.frontend_url for c in CaseMetadata.objects.filter(robots_txt_until__gte=timezone.now(), no_index=True)]
    )+"\n", content_type="text/plain")

def series(request, series_slug):
    """ /<series_slug>/ -- list all volumes for each series with that slug (typically only one). """
    # redirect if series slug is in the wrong format

    if slugify(series_slug) != series_slug:
        return HttpResponseRedirect(helpers.reverse('series', args=[slugify(series_slug)], host='cite'))
    reporters = list(Reporter.objects
        .filter(short_name_slug=series_slug)
        .prefetch_related(Prefetch('volumes', queryset=VolumeMetadata.objects.exclude(volume_number=None).exclude(volume_number='').exclude(duplicate=True).exclude(out_of_scope=True)))
        .order_by('full_name'))
    if not reporters:
        raise Http404
    reporters = [(reporter, sorted(reporter.volumes.all(), key=lambda volume: natural_sort_key(volume.volume_number))) for reporter in reporters]
    return render(request, 'cite/series.html', {
        "reporters": reporters,
    })

def volume(request, series_slug, volume_number_slug):
    """ /<series_slug>/<volume_number>/ -- list all cases for given volumes (typically only one). """

    # this is to preserve compatibility with old links based on the unslugged volume number
    volume_number_slug = slugify(volume_number_slug)

    # redirect if series slug is in the wrong format

    if slugify(series_slug) != series_slug:
        return HttpResponseRedirect(helpers.reverse('volume', args=[slugify(series_slug), volume_number_slug], host='cite'))

    cases_query = CaseDocument.search()\
        .filter("term", volume__volume_number_slug=volume_number_slug)\
        .filter("term", reporter__short_name_slug__raw=series_slug)\
        .sort('first_page')\
        .extra(size=10000)
    cases_query.aggs.bucket('vols', 'terms', field='volume.barcode')
    cases = cases_query.execute()

    if len(cases) == 0:
        raise Http404

    volume_filters = None
    for vol in cases.aggs.vols.buckets:
        if volume_filters is None:
            volume_filters = Q(barcode=vol.key)
        else:
            volume_filters = volume_filters | Q(barcode=vol.key)
    vols = VolumeMetadata.objects.select_related('reporter').filter(volume_filters).all()
    if not vols:
        raise Http404

    volumes = [(volume, [ case for case in sorted(cases, key=lambda case: natural_sort_key(case.first_page or '')) if case.volume.barcode == volume.barcode]) for volume in vols ]

    return render(request, 'cite/volume.html', {
        "volumes": volumes,
    })

def citation(request, series_slug, volume_number_slug, page_number, case_id=None):
    """
        /<series_slug>/<volume_number>/<page_number>/                       -- show requested case (or list of cases, or case not found page).
        /<series_slug>/<volume_number>/<page_number>/<case_id>/             -- show requested case, using case_id to find one of multiple cases at this cite
    """

    # this is to preserve compatibility with old links based on the unslugged volume number
    volume_number_slug = slugify(volume_number_slug)

    # redirect if series slug is in the wrong format
    if slugify(series_slug) != series_slug:
        if case_id:
            return HttpResponseRedirect(helpers.reverse('citation',
                                                    args=[slugify(series_slug), volume_number_slug, page_number, case_id],
                                                    host='cite'))
        else:
            return HttpResponseRedirect(helpers.reverse('citation',
                                                        args=[slugify(series_slug), volume_number_slug, page_number],
                                                        host='cite'))

    ### try to look up citation
    full_cite = "%s %s %s" % (volume_number_slug, series_slug.replace('-', ' ').title(), page_number)
    normalized_cite = re.sub(r'[^0-9a-z]', '', full_cite.lower())

    if case_id:
        try:
            cases = [ CaseDocument.get(id=case_id) ]
        except NotFoundError:
            cases = CaseDocument.search().filter("term", citations__normalized_cite=normalized_cite).execute()
    else:
        cases = CaseDocument.search().filter("term", citations__normalized_cite=normalized_cite).execute()

    ### handle case where we found a unique case with that citation
    if cases and len(cases) == 1:

        case = cases[0]

        # handle whitelisted case or logged-in user
        if case.jurisdiction.whitelisted or request.user.is_authenticated:
            serializer = serializers.CaseDocumentSerializerWithCasebody

        # handle logged-out user with cookies set up already
        elif 'case_allowance_remaining' in request.session and request.COOKIES.get('not_a_bot', 'no') == 'yes':
            with locked_session(request) as session:
                cases_remaining = session['case_allowance_remaining']

                # handle daily quota reset
                if session['case_allowance_last_updated'] < time.time() - 60*60*24:
                    cases_remaining = settings.API_CASE_DAILY_ALLOWANCE
                    session['case_allowance_last_updated'] = time.time()

                # if quota remaining, serialize without checking credentials
                if cases_remaining > 0:
                    session['case_allowance_remaining'] = cases_remaining - 1
                    serializer = serializers.NoLoginCaseDocumentSerializer

                # if quota used up, use regular serializer that checks credentials
                else:
                    serializer = serializers.CaseDocumentSerializerWithCasebody

        # handle google crawler
        elif helpers.is_google_bot(request):
            serializer = serializers.NoLoginCaseDocumentSerializer

        # if non-whitelisted case, not logged in, and no cookies set up, redirect to ?set_cookie=1
        else:
            request.session['case_allowance_remaining'] = settings.API_CASE_DAILY_ALLOWANCE
            request.session['case_allowance_last_updated'] = time.time()
            return HttpResponseRedirect('%s?%s' % (helpers.reverse('set_cookie', host='cite'), urlencode({'next': request.get_full_path()})))

        # render case using API serializer
        api_request = Request(request, authenticators=[SessionAuthentication()])
        api_request.accepted_renderer = HTMLRenderer()
        serialized = serializer(case, context={'request': api_request})
        context = {'request': api_request, 'meta_tags': []}
        if not case.jurisdiction.whitelisted:
            # blacklisted cases shouldn't show cached version in google search results
            context['meta_tags'].append({"name": "googlebot", "content": "noarchive"})

        # This should probably change
        if hasattr(case, 'no_index'):
            if case.no_index:
                context['meta_tags'].append({"name": "robots", "content": "noindex"})
        else:
            if CaseMetadata.objects.get(pk=case.id).no_index:
                context['meta_tags'].append({"name": "robots", "content": "noindex"})

        rendered = HTMLRenderer().render(serialized.data, renderer_context=context)
        return HttpResponse(rendered)

    ### handle non-unique citation (zero or multiple)
    else:

        reporter = Reporter.objects.filter(short_name_slug=slugify(series_slug)).first()
        series = reporter.short_name if reporter else series_slug

        return render(request, 'cite/citation_failed.html', {
            "cases": cases,
            "full_cite": full_cite,
            "series_slug": series_slug,
            "series": series,
            "volume_number_slug": volume_number_slug,
            "page_number": page_number,
        })

def set_cookie(request):
    """
        /set_cookie/          -- try to use javascript to set a 'not_a_bot=1' cookie
        /set_cookie/?no_js=1  -- ask user to click a button to set a 'not_a_bot=1' cookie
    """
    # user is actually a google bot
    if helpers.is_google_bot(request):
        return safe_redirect(request)

    # user already had a not_a_bot cookie and just needed a session cookie,
    # which was set when they were forwarded here -- they're ready to go:
    elif 'case_allowance_remaining' in request.session and request.COOKIES.get('not_a_bot', 'no') == 'yes':
        return safe_redirect(request)

    # user has successfully POSTed to get their not_a_bot cookie:
    elif request.method == 'POST' and request.POST.get('not_a_bot') == 'yes':
        response = safe_redirect(request)
        response.set_cookie('not_a_bot', 'yes', max_age=60 * 60 * 24 * 365 * 100)
        return response

    # user failed the JS check, so has to click the button by hand:
    elif 'no_js' in request.GET:
        return render(request, 'cite/set_cookie.html', {
            'next': request.GET.get('next', '/'),
        })

    # try to use JS to click button for user:
    else:
        return render(request, 'cite/check_js.html', {
            'next': request.GET.get('next', '/'),
        })
