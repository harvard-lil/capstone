import re
import time
from collections import defaultdict
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, QueryDict
from django.shortcuts import render
from django.utils import timezone
from rest_framework.request import Request

from capapi import serializers
from capapi.authentication import SessionAuthentication
from capapi.renderers import HTMLRenderer
from capdb.models import Reporter, VolumeMetadata, Citation, CaseMetadata

### helpers ###

def replace_query_params(url, **query_params):
    """
        Return URL with query_params inserted or updated. If a value is None, param will be removed.
    """
    (scheme, netloc, path, params, query, fragment) = urlparse(url)
    query_dict = QueryDict(query).copy()
    for k, v in query_params.items():
        if v is None:
            query_dict.pop(k, None)
        else:
            query_dict[k] = v
    return urlunparse((scheme, netloc, path, params, query_dict.urlencode(), fragment))

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
    reporters = Reporter.objects.all().prefetch_related('jurisdictions').order_by('full_name')
    reporters_by_jurisdiction = defaultdict(list)
    for reporter in reporters:
        for jurisdiction in reporter.jurisdictions.all():
            reporters_by_jurisdiction[jurisdiction].append(reporter)

    # prepare (jurisdiction, reporters) list
    jurisdictions = sorted(reporters_by_jurisdiction.items(), key=lambda item: item[0].name)

    return render(request, 'cite/home.html', {
        "jurisdictions": jurisdictions,
    })

def series(request, series_slug):
    """ /<series_slug>/ -- list all volumes for each series with that slug (typically only one). """
    reporters = list(Reporter.objects.filter(short_name_slug=series_slug).prefetch_related('volumes').order_by('full_name'))
    if not reporters:
        raise Http404
    return render(request, 'cite/series.html', {
        "reporters": reporters,
    })

def volume(request, series_slug, volume_number):
    """ /<series_slug>/<volume_number>/ -- list all cases for given volumes (typically only one). """
    volumes = list(VolumeMetadata.objects
        .filter(reporter__short_name_slug=series_slug, volume_number=volume_number)
        .select_related('reporter')
        .prefetch_related('case_metadatas__citations'))
    if not volumes:
        raise Http404
    return render(request, 'cite/volume.html', {
        "volumes": volumes,
    })

def citation(request, series_slug, volume_number, page_number, case_id=None):
    """
        /<series_slug>/<volume_number>/<page_number>/                       -- show requested case (or list of cases, or case not found page).
        /<series_slug>/<volume_number>/<page_number>/<case_id>/             -- show requested case, using case_id to find one of multiple cases at this cite
        /<series_slug>/<volume_number>/<page_number>/?set_cookie=1          -- try to use javascript to set a 'not_a_bot=1' cookie
        /<series_slug>/<volume_number>/<page_number>/?set_cookie=1&no_js=1  -- ask user to click a button to set a 'not_a_bot=1' cookie
    """

    ### handle logged-out user who was redirected here with ?set_cookie=1
    if 'set_cookie' in request.GET:

        # user already had a not_a_bot cookie and just needed a session cookie -- they're ready to go:
        if 'case_allowance_remaining' in request.session and request.COOKIES.get('not_a_bot', 'no') == 'yes':
            return HttpResponseRedirect(replace_query_params(request.get_full_path(), set_cookie=None, no_js=None))

        # user has successfully POSTed to get their not_a_bot cookie:
        elif request.method == 'POST' and request.POST.get('not_a_bot') == 'yes':
            response = HttpResponseRedirect(replace_query_params(request.get_full_path(), set_cookie=None, no_js=None))
            response.set_cookie('not_a_bot', 'yes', max_age=60*60*24*365*100)
            return response

        # user failed the JS check, so has to click the button by hand:
        elif 'no_js' in request.GET:
            return render(request, 'cite/set_cookie.html')

        # try to use JS to click button for user:
        else:
            return render(request, 'cite/check_js.html')

    ### try to look up citation
    full_cite = "%s %s %s" % (volume_number, series_slug.replace('-', ' ').title(), page_number)
    normalized_cite = re.sub(r'[^0-9a-z]', '', full_cite.lower())
    citations = Citation.objects.filter(normalized_cite=normalized_cite)
    if case_id:
        citations = citations.filter(case_id=case_id)
    citations = list(citations)

    ### handle case where we found a unique case with that citation
    if len(citations) == 1:

        # look up case data
        case = CaseMetadata.objects\
            .select_related('case_xml', 'body_cache')\
            .prefetch_related('citations')\
            .defer('body_cache__xml', 'body_cache__text', 'body_cache__json') \
            .get(citations=citations[0])

        # handle whitelisted case or logged-in user
        if case.jurisdiction_whitelisted or request.user.is_authenticated:
            serializer = serializers.CaseSerializerWithCasebody

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
                    serializer = serializers.NoLoginCaseSerializer

                # if quota used up, use regular serializer that checks credentials
                else:
                    serializer = serializers.CaseSerializerWithCasebody

        # if non-whitelisted case, not logged in, and no cookies set up, redirect to ?set_cookie=1
        else:
            request.session['case_allowance_remaining'] = settings.API_CASE_DAILY_ALLOWANCE
            request.session['case_allowance_last_updated'] = time.time()
            return HttpResponseRedirect(replace_query_params(request.get_full_path(), set_cookie='1'))

        # render case using API serializer
        api_request = Request(request, authenticators=[SessionAuthentication()])
        api_request.accepted_renderer = HTMLRenderer()
        serialized = serializer(case, context={'request': api_request})
        rendered = HTMLRenderer().render(serialized.data, renderer_context={'request': api_request})
        return HttpResponse(rendered)

    ### handle non-unique citation (zero or multiple)
    else:
        return render(request, 'cite/citation_failed.html', {
            "citations": citations,
            "full_cite": full_cite,
        })
