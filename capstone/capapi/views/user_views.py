from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from capapi import models as capapi_models, resources
from capapi.forms import RegisterUserForm, ResendVerificationForm
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
        error = None
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
    return render(request, 'registration/user-account.html')





