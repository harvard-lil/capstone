import re
import time
import json
from collections import defaultdict
from contextlib import contextmanager
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import SuspiciousOperation
from django.forms import model_to_dict
from django.urls import NoReverseMatch
from django.db import transaction
from django.db.models import Prefetch
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework.request import Request
from elasticsearch.exceptions import NotFoundError
from natsort import natsorted

from capapi import serializers
from capapi.documents import CaseDocument
from capapi.authentication import SessionAuthentication
from capapi.resources import apply_replacements, link_to_cites
from capdb.models import Reporter, VolumeMetadata, CaseMetadata, Citation, CaseFont, PageStructure, EditLog
from capweb.helpers import reverse, is_google_bot
from cite.helpers import geolocate
from config.logging import logger


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
    return render(request, "cite/robots.txt", {
        'cases': CaseMetadata.objects.filter(robots_txt_until__gte=timezone.now()),
    }, content_type="text/plain")

def series(request, series_slug):
    """ /<series_slug>/ -- list all volumes for each series with that slug (typically only one). """
    # redirect if series slug is in the wrong format
    try:
        if slugify(series_slug) != series_slug:
            return HttpResponseRedirect(reverse('series', args=[slugify(series_slug)], host='cite'))
    except NoReverseMatch:
        raise Http404
    reporters = list(Reporter.objects
        .filter(short_name_slug=series_slug)
        .exclude(start_year=None)
        .prefetch_related(Prefetch('volumes', queryset=VolumeMetadata.objects.exclude(volume_number=None).exclude(volume_number='').exclude(duplicate=True).exclude(out_of_scope=True)))
        .order_by('full_name'))
    if not reporters:
        raise Http404
    reporters = [(reporter, natsorted(reporter.volumes.all(), key=lambda volume: volume.volume_number)) for reporter in reporters]
    return render(request, 'cite/series.html', {
        "reporters": reporters,
    })

def volume(request, series_slug, volume_number_slug):
    """ /<series_slug>/<volume_number>/ -- list all cases for given volumes (typically only one). """

    # redirect if series slug or volume number slug is in the wrong format

    if slugify(series_slug) != series_slug or slugify(volume_number_slug) != volume_number_slug:
        return HttpResponseRedirect(reverse('volume', args=[slugify(series_slug), slugify(volume_number_slug)], host='cite'))

    cases_query = CaseDocument.search()\
        .filter("term", volume__volume_number_slug=volume_number_slug)\
        .filter("term", reporter__short_name_slug__raw=series_slug)\
        .sort('first_page')\
        .extra(size=10000)\
        .source({"excludes": "casebody_data.*"})
    cases_query.aggs.bucket('vols', 'terms', field='volume.barcode')
    cases = cases_query.execute()

    if len(cases) == 0:
        raise Http404

    volume_ids = [vol.key for vol in cases.aggs.vols.buckets]
    vols = list(VolumeMetadata.objects.select_related('reporter').filter(pk__in=volume_ids))
    if not vols:
        raise Http404

    volumes = [(volume, [ case for case in natsorted(cases, key=lambda case: case.first_page) if case.volume.barcode == volume.barcode]) for volume in vols ]

    return render(request, 'cite/volume.html', {
        "volumes": volumes,
    })


def case_pdf(request, case_id, pdf_name):
    """
        Return the PDF for a case. This wraps citation() so that all rules about quotas and anonymous users can be
        applied before we return the case.
    """
    # check that we are at the canonical URL
    case = get_object_or_404(CaseMetadata.objects.select_related('volume').prefetch_related('citations'), pk=case_id)
    pdf_url = case.get_pdf_url()
    if request.build_absolute_uri() != pdf_url:
        return HttpResponseRedirect(pdf_url)

    return citation(request,None, None, None, case_id, pdf=True, db_case=case)


@staff_member_required
def page_image(request, series_slug, volume_number_slug, sequence_number):
    """
        Return the image for a page to authorized users.
    """
    vol = get_object_or_404(VolumeMetadata, reporter__short_name_slug=slugify(series_slug), volume_number_slug=volume_number_slug)
    return HttpResponse(vol.extract_page_image(int(sequence_number), zoom_level=2.0), content_type="image/png")


@staff_member_required
@ensure_csrf_cookie
def case_editor(request, case_id):
    case = get_object_or_404(CaseMetadata.objects.select_related('volume', 'reporter', 'structure'), pk=case_id)
    pages = list(case.structure.pages.all())
    metadata_fields = ['name', 'decision_date_original', 'docket_number']

    # handle save
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf8'))

        # update case, if needed
        case_to_save = None
        metadata_count = 0
        for field in metadata_fields:
            if field not in data['metadata']:
                continue
            old_val, new_val = data['metadata'][field]
            if getattr(case, field) == old_val:
                metadata_count += 1
                setattr(case, field, new_val)
                case_to_save = case

        # update pages, if needed
        pages_to_save = []
        word_count = 0
        if data['edit_list']:
            pages_by_id = {p.id: [p, PageStructure.blocks_by_id([p])] for p in pages}
            for page_id, blocks in data['edit_list'].items():
                page, blocks_by_id = pages_by_id[int(page_id)]
                pages_to_save.append(page)
                for block_id, block_edit_list in blocks.items():
                    block = blocks_by_id[block_id]
                    tokens = block.get('tokens')
                    if not tokens:
                        raise Exception("attempt to edit block without tokens")
                    word_count += 1
                    for index, [old_val, new_val] in block_edit_list.items():
                        index = int(index)
                        old_token = tokens[index]
                        if type(old_token) != str:
                            raise Exception("attempt to edit non-string token")
                        if old_token != old_val:
                            raise Exception("attempt to edit out-of-date token")
                        tokens[index] = new_val

        if case_to_save or pages_to_save:
            with EditLog(description='Case %s edited by user %s: %s metadata fields, %s words' % (case.id, request.user.id, metadata_count, word_count)).record():
                if case_to_save:
                    case.save()
                if pages_to_save:
                    PageStructure.objects.bulk_update(pages_to_save, ['blocks'])
                    case.sync_case_body_cache(blocks_by_id=PageStructure.blocks_by_id(pages))

        return HttpResponse('OK')

    # serialize values for JS
    case_json = json.dumps(model_to_dict(case, fields=['id'] + metadata_fields))
    pages_json = json.dumps([
        {
            'id': page.id,
            'width': page.width,
            'height': page.height,
            "image_url": reverse('page_image', [case.reporter.short_name_slug, case.volume.volume_number_slug, page.order]),
            "blocks": page.blocks,
        } for page in case.structure.pages.all()
    ])
    fonts = CaseFont.fonts_by_id(PageStructure.blocks_by_id(pages))
    fonts_json = json.dumps({k: model_to_dict(v) for k, v in fonts.items()})

    return render(request, 'cite/case_editor.html', {
        'case': case,
        'case_json': case_json,
        'pages_json': pages_json,
        'fonts_json': fonts_json,
        'citation_full': case.full_cite(),
    })


def citation(request, series_slug, volume_number_slug, page_number, case_id=None, pdf=False, db_case=None):
    """
        /<series_slug>/<volume_number>/<page_number>/                       -- show requested case (or list of cases, or case not found page).
        /<series_slug>/<volume_number>/<page_number>/<case_id>/             -- show requested case, using case_id to find one of multiple cases at this cite
    """

    # redirect if series slug or volume number slug is in the wrong format
    if not pdf and (slugify(series_slug) != series_slug or slugify(volume_number_slug) != volume_number_slug):
        return HttpResponseRedirect(reverse(
            'citation',
            args=[slugify(series_slug), slugify(volume_number_slug), page_number] + ([case_id] if case_id else []),
            host='cite'))

    ### try to look up citation
    if case_id:
        try:
            case = CaseDocument.get(id=case_id)
        except NotFoundError:
            raise Http404
    else:
        full_cite = "%s %s %s" % (volume_number_slug, series_slug.replace('-', ' ').title(), page_number)
        normalized_cite = re.sub(r'[^0-9a-z]', '', full_cite.lower())
        cases = CaseDocument.search().filter("term", citations__normalized_cite=normalized_cite).execute()

        ### handle non-unique citation (zero or multiple)
        if not cases or len(cases) != 1:
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
    elif is_google_bot(request):
        serializer = serializers.NoLoginCaseDocumentSerializer

    # if non-whitelisted case, not logged in, and no cookies set up, redirect to ?set_cookie=1
    else:
        request.session['case_allowance_remaining'] = settings.API_CASE_DAILY_ALLOWANCE
        request.session['case_allowance_last_updated'] = time.time()
        return HttpResponseRedirect('%s?%s' % (reverse('set_cookie', host='cite'), urlencode({'next': request.get_full_path()})))

    # render case using API serializer
    api_request = Request(request, authenticators=[SessionAuthentication()])
    serialized = serializer(case, context={'request': api_request, 'force_body_format': 'html'})
    serialized_data = serialized.data

    # handle pdf output --
    # wait until here to do this so serializer() can apply case quotas
    db_case = db_case or CaseMetadata.objects.select_related('volume').prefetch_related('citations').get(pk=case.id)
    can_render_pdf = db_case.volume.pdf_file and not db_case.no_index_redacted and settings.CASE_PDF_FEATURE and serialized_data['casebody']['status'] == 'ok'
    if pdf:
        if serialized_data['casebody']['status'] != 'ok':
            return HttpResponseRedirect(db_case.get_full_frontend_url())
        if not can_render_pdf:
            raise Http404
        return HttpResponse(db_case.get_pdf(), content_type="application/pdf")

    # HTML output

    # meta tags
    meta_tags = []
    if not case.jurisdiction.whitelisted:
        # blacklisted cases shouldn't show cached version in google search results
        meta_tags.append({"name": "googlebot", "content": "noarchive"})
    if db_case.no_index:
        meta_tags.append({"name": "robots", "content": "noindex"})

    case_html = None
    if serialized_data['casebody']['status'] == 'ok':
        case_html = serialized_data['casebody']['data']
        footer_message = db_case.custom_footer_message or ''

        # link all captured cites
        case_html = link_to_cites(case_html, serialized_data['cites_to'])

        # insert redactions
        if db_case.no_index_redacted:
            case_html = apply_replacements(case_html, db_case.no_index_redacted)
            db_case.name = apply_replacements(db_case.name, db_case.no_index_redacted)
            db_case.name_abbreviation = apply_replacements(db_case.name_abbreviation, db_case.no_index_redacted)
            footer_message += "Some text has been redacted. \n"

        # insert elisions
        if db_case.no_index_elided:
            elision_span = "<span class='elision-help-text' style='display: none'>hide</span>" \
                           "<span class='elided-text' role='button' tabindex='0' data-hidden-text='%s'>%s</span>"
            replacements = {k: elision_span % (k, v) for k, v in db_case.no_index_elided.items()}
            case_html = apply_replacements(case_html, replacements, prefix="", suffix="")
            db_case.name = apply_replacements(db_case.name, replacements, prefix="", suffix="")
            db_case.name_abbreviation = apply_replacements(db_case.name_abbreviation, replacements, prefix="", suffix="")
            footer_message += "Some text has been hidden for privacy from automated systems, but can be revealed by clicking the elided text. \n"

        if footer_message:
            case_html += "<hr/><footer class='custom-case-footer'>%s</footer>" % footer_message.replace('\n', '<br>')

    if settings.GEOLOCATION_FEATURE and request.META.get('HTTP_X_FORWARDED_FOR'):
        # Trust x-forwarded-for in this case because we don't mind being lied to, and would rather show accurate
        # results for users using honest proxies.
        try:
            location = geolocate(request.META['HTTP_X_FORWARDED_FOR'].split(',')[-1])
            location_str = location.country.name
            if location.subdivisions:
                location_str = "%s, %s" % (location.subdivisions.most_specific.name, location_str)
            logger.info("Someone from %s read a case from %s." % (location_str, case.court.name))
        except Exception as e:
            logger.warning("Unable to geolocate %s: %s" % (request.user.ip_address, e))

    # set CSRF token for staff so they can make ajax requests
    if request.user.is_staff:
        get_token(request)

    formatted_name = db_case.name.replace(' v. ', ' <span class="case-name-v">v.</span> ')

    return render(request, 'cite/case.html', {
        'meta_tags': meta_tags,
        'can_render_pdf': can_render_pdf,
        'db_case': db_case,
        'es_case': serialized_data,
        'status': serialized_data['casebody']['status'],
        'case_html': case_html,
        'citation_full': db_case.full_cite(),
        'citations': ", ".join(c.cite for c in Citation.sorted_by_type(db_case.citations.all())),
        'formatted_name': formatted_name,
    })


def set_cookie(request):
    """
        /set_cookie/          -- try to use javascript to set a 'not_a_bot=1' cookie
        /set_cookie/?no_js=1  -- ask user to click a button to set a 'not_a_bot=1' cookie
    """
    # user is actually a google bot
    if is_google_bot(request):
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


@require_POST
@staff_member_required
def redact_case(request, case_id):
    """
        Admin-only view to redact or elide selected text from case browser.
    """
    case = get_object_or_404(CaseMetadata, pk=case_id)
    if request.POST['kind'] == 'redact':
        if not case.no_index_redacted:
            case.no_index_redacted = {}
        target = case.no_index_redacted
        replacement = 'redacted'
    else:
        if not case.no_index_elided:
            case.no_index_elided = {}
        target = case.no_index_elided
        replacement = '...'
    target[request.POST['text']] = replacement
    case.robots_txt_until = timezone.now() + timedelta(days=7)
    case.save()
    return HttpResponse('ok')