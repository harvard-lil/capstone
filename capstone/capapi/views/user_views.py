from pathlib import Path
from wsgiref.util import FileWrapper
from collections import OrderedDict

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.http import StreamingHttpResponse, Http404

from capapi import models as capapi_models, resources
from capapi.forms import RegisterUserForm, ResendVerificationForm
from capapi.middleware import add_cache_header
from capapi.models import SiteLimits
from capapi.resources import form_for_request


def register_user(request):
    """ Create new user """
    form = form_for_request(request, RegisterUserForm)

    if request.method == 'POST' and form.is_valid():
        form.save()
        resources.send_new_signup_email(request, form.instance)
        return render(request, 'registration/sign-up-success.html', {
            'status': 'Success!',
            'message': 'Thank you. Please check your email for a verification link.'
        })

    return render(request, 'registration/sign-up.html', {'form': form})


def verify_user(request, user_id, activation_nonce):
    """ Verify email and assign api token """
    try:
        user = capapi_models.CapUser.objects.get(pk=user_id)
        user.authenticate_user(activation_nonce=activation_nonce)
    except (capapi_models.CapUser.DoesNotExist, PermissionDenied):
        error = "Unknown verification code."
    else:
        # user authenticated successfully
        error = None

        # update API limits for first 50 users per day
        site_limits = SiteLimits.add_values(daily_signups=1)
        if site_limits.daily_signups < site_limits.daily_signup_limit:
            user.total_case_allowance = user.case_allowance_remaining = settings.API_CASE_DAILY_ALLOWANCE
            user.save()
    return render(request, 'registration/verified.html', {
        'contact_email': settings.API_EMAIL_ADDRESS,
        'error': error,
    })


def resend_verification(request):
    """ Resend verification code """
    form = form_for_request(request, ResendVerificationForm)

    if request.method == 'POST' and form.is_valid():
        try:
            user = capapi_models.CapUser.objects.get(email=form.cleaned_data['email'])
        except capapi_models.CapUser.DoesNotExist:
            form.add_error('email', "User with that email does not exist.")
        else:
            if user.email_verified:
                form.add_error('email', "Email address is already verified.")
        if form.is_valid():
            resources.send_new_signup_email(request, user)
            return render(request, 'registration/sign-up-success.html', {
                'status': 'Success!',
                'message': 'Thank you. Please check your email %s for a verification link.' % user.email
            })
    return render(request, 'registration/resend-nonce.html', {
        'info_email': settings.API_EMAIL_ADDRESS,
        'form': form,
    })


@login_required
def user_details(request):
    """ Show user details """
    request.user.update_case_allowance()
    context = {'unlimited': request.user.unlimited_access_in_effect()}
    return render(request, 'registration/user-account.html', context)


def bulk(request):
    """ List zips available for download """
    def get_zips(folder):
        # helper to fetch public or private zips, returning {'Jurisdiction': ['file_name', 'file_name']}
        path = Path(settings.BULK_DATA_DIR, folder)
        zip_groups = OrderedDict()
        for zip_path in sorted(path.glob('*/*.zip'), key=lambda x: x.parts):
            jurisdiction, file_name = zip_path.parts[-2:]
            zip_groups.setdefault(jurisdiction, []).append([file_name, zip_path.stat().st_size])
        return zip_groups

    public_zips = get_zips('public')
    private_zips = get_zips('private') if request.user.unlimited_access_in_effect() else []

    return render(request, 'bulk.html', {
        'public_zips': public_zips,
        'private_zips': private_zips,
    })


def bulk_download(request, public_or_private, jur, filename):
    """
    View for downloading zipped jurisdiction files
    """
    # enforce permissions
    if public_or_private == 'private':
        if not request.user.unlimited_access_in_effect():
            raise PermissionDenied
    elif public_or_private != 'public':
        raise Http404

    # make sure requested file is a zip and exists
    file_path = Path(settings.BULK_DATA_DIR, public_or_private, jur, filename)
    if file_path.suffix != '.zip' or not file_path.exists():
        raise Http404

    # send file
    response = StreamingHttpResponse(FileWrapper(file_path.open('rb')), content_type='application/zip')
    response['Content-Length'] = file_path.stat().st_size
    response['Content-Disposition'] = 'attachment; filename="%s"' % file_path.name

    # public downloads are cacheable
    if public_or_private == 'public':
        add_cache_header(response)

    return response
