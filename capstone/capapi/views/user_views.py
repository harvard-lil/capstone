from collections import OrderedDict
from copy import copy
from datetime import datetime

from mailchimp3 import MailChimp
from mailchimp3.mailchimpclient import MailChimpError

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail, EmailMessage
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.utils import timezone
from django.utils.safestring import mark_safe

from capapi import resources
from capapi.forms import RegisterUserForm, ResendVerificationForm, ResearchContractForm, HarvardContractForm
from capapi.models import SiteLimits, CapUser, ResearchContract
from capapi.resources import form_for_request
from capapi.views.api_views import UserHistoryViewSet
from capdb.models import CaseExport
from capweb.helpers import reverse, user_has_harvard_email
from config.logging import logger
from user_data.models import UserHistory


def register_user(request):
    """ Create new user """
    if not request.user.is_anonymous:
        return HttpResponseRedirect(reverse('user-details'))

    if settings.DISABLE_SIGNUPS:
        return HttpResponseRedirect('/')

    form = form_for_request(request, RegisterUserForm)
    if request.method == 'POST' and form.is_valid():
        form.save()
        resources.send_new_signup_email(request, form.instance)
        return render(request, 'registration/sign-up-success.html', {
            'status': 'Success!',
            'message': 'Thank you. Please check your email for a verification link.',
        })

    return render(request, 'registration/register.html', {'form': form})


def verify_user(request, user_id, activation_nonce):
    """ Verify email and assign api token """
    user = get_object_or_404(CapUser, pk=user_id)

    # This leaks a little info -- we reveal whether a user ID exists or not and whether it is verified or deactivated.
    # This seems acceptable to provide better messages to legitimate users.
    if user.email_verified:
        return render(request, 'registration/verified.html')
    if not user.is_active:
        return render(request, 'registration/verified.html', {'error': 'This account is not active and cannot be verified.'})

    error = None
    mailing_list_message = "We have not signed you up for our newsletter, Lawvocado. Sign up any time from our homepage."
    try:
        user.authenticate_user(activation_nonce=activation_nonce)
    except PermissionDenied:
        error = mark_safe("This verification code is invalid or expired. <a href='%s'>Resend verification</a>?" % reverse('resend-verification'))
    else:
        # user authenticated successfully

        # update API limits for first X users per day
        # users after this limit will have approved accounts, but we will have to go back manually to increase limits
        site_limits = SiteLimits.add_values(daily_signups=1)
        if site_limits.daily_signups < site_limits.daily_signup_limit:
            user.total_case_allowance = user.case_allowance_remaining = settings.API_CASE_DAILY_ALLOWANCE
            user.save()

        # sign them up for the mailing list if they selected the mailing_list checkbox.
        if settings.MAILCHIMP['api_key'] and user.mailing_list:
            try:
                mc_client = MailChimp(mc_api=settings.MAILCHIMP['api_key'], mc_user=settings.MAILCHIMP['api_user'])
                mc_client.lists.members.create(
                    settings.MAILCHIMP['id'], {
                        'email_address': user.email,
                        'merge_fields': {'LNAME': user.first_name, 'FNAME': user.last_name},
                        'status': 'subscribed'
                    })
                mailing_list_message = "Also, thanks for signing up for our newsletter, Lawvocado."
            except MailChimpError as e:
                if e.args[0]['status'] == 400 and e.args[0]['title'] == 'Member Exists':
                    mailing_list_message = "Also, thanks for your continued interest in our newsletter, " \
                                           "Lawvocado. We'll keep you on our list."
                else:
                    logger.exception("Error adding user email %s to mailing list" % user.email)

    return render(request, 'registration/verified.html', {
        'error': error,
        'mailing_list_message': mailing_list_message,
    })


def resend_verification(request):
    """ Resend verification code """
    form = form_for_request(request, ResendVerificationForm)

    if request.method == 'POST' and form.is_valid():
        try:
            user = CapUser.objects.get(email=form.cleaned_data['email'])
        except CapUser.DoesNotExist:
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
        'info_email': settings.DEFAULT_FROM_EMAIL,
        'form': form,
    })


@login_required
def user_details(request):
    """ Show user details """
    request.user.update_case_allowance()
    context = {
        'research_contract': request.user.research_contracts.filter(status='pending').first(),
        'research_request': request.user.research_requests.filter(status='pending').first(),
    }
    return render(request, 'registration/user-details.html', context)


@login_required
def user_history(request):
    """ Show user history. """
    # handle updating or deleting user history settings
    if request.method == 'POST':
        user = request.user
        if request.POST.get('delete') == 'true':
            UserHistory.objects.filter(user_id=user.id).delete()
            user.has_tracked_history = False
            user.save()
        elif request.POST.get('toggle_tracking') == 'true':
            user.track_history = not user.track_history
            user.save()

    # get history data from API
    api_request = copy(request)
    api_request.method = 'GET'
    data = UserHistoryViewSet.as_view({'get': 'list'})(api_request).data

    # parse dates
    for result in data['results']:
        result['date'] = datetime.strptime(result['date'], "%Y-%m-%dT%H:%M:%S.%fZ")

    return render(request, 'registration/user-history.html', {
        'next': data['next'].split('?')[1] if data['next'] else None,
        'previous': data['previous'].split('?')[1] if data['previous'] else None,
        'results': data['results'],
    })


@login_required
@user_has_harvard_email()
def request_harvard_research_access_intro(request):
    """ Warning shown before Harvard access page """
    if settings.DISABLE_SIGNUPS:
        return HttpResponseRedirect('/')

    return render(request, 'research_request/harvard_research_request_intro.html')


@login_required
@user_has_harvard_email()
def request_harvard_research_access(request):
    """ Sign Harvard-email based contract """
    if settings.DISABLE_SIGNUPS:
        return HttpResponseRedirect('/')

    name = "%s %s" % (request.user.first_name, request.user.last_name)
    form = form_for_request(request, HarvardContractForm, initial={'name': name, 'email': request.user.email})

    if request.method == 'POST' and form.is_valid():
        # save request object
        contract = form.instance
        contract.user = request.user
        contract.email = request.user.email
        contract.contract_html = loader.get_template('research_request/contracts/harvard_rendered.html').render({
            'form': form
        })
        form.save()
        request.user.harvard_access = True
        request.user.save()

        # send notice emails
        message = loader.get_template('research_request/emails/harvard_contract_email.html').render({
            'contract_html': contract.contract_html,
            'signed_date': contract.user_signature_date,
        })
        subject = 'CAP Bulk Access Agreement for {}'.format(name)
        msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL, request.user.email])
        msg.content_subtype = "html"  # Main content is text/html
        msg.send()

        return HttpResponseRedirect(reverse('harvard-research-request-success'))

    return render(request, 'research_request/harvard_research_request.html', {'form': form})


@login_required
def request_research_access(request):
    """ Sign academic/nonprofit based contract """
    if settings.DISABLE_SIGNUPS:
        return HttpResponseRedirect('/')

    name = "%s %s" % (request.user.first_name, request.user.last_name)
    form = form_for_request(request, ResearchContractForm, initial={'name': name, 'email': request.user.email})

    if request.method == 'POST' and form.is_valid():
        # save contract object
        form.instance.user = request.user
        form.instance.contract_html = loader.get_template('research_request/contracts/scholar_rendered.html').render({
            'form': form
        })
        form.save()

        # send notice emails
        message = loader.get_template('research_request/emails/contract_request_email.txt').render({
            'data': form.cleaned_data,
            'approval_url': reverse('research-approval', scheme='https'),
        })
        emails = [settings.DEFAULT_FROM_EMAIL] + \
                 [user.email for user in CapUser.objects.filter(groups__name='contract_approvers')]
        subject = 'CAP research scholar application for {}'.format(name)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails)

        return HttpResponseRedirect(reverse('research-request-success'))

    return render(request, 'research_request/research_request.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.groups.filter(name='contract_approvers').exists())
def approve_research_access(request):
    """ Approve or reject contract applications """
    approver_message = None
    if request.method == 'POST':
        contract = get_object_or_404(ResearchContract, id=request.POST.get('contract_id'))
        contract.approver = request.user
        contract.approver_notes = request.POST.get('approver_notes')
        contract.approver_signature_date = timezone.now()
        if request.POST.get('approve') == "true":
            with transaction.atomic():
                # update contract
                contract.status = 'approved'
                contract.save()

                # update user for unlimited access
                contract.user.unlimited_access = True
                contract.user.save()

                # send contract email
                # we send this as html-only so we can use the same HTML in the contract signing page and the
                # resulting rendered contract
                message = loader.get_template('research_request/emails/contract_approved_email.html').render({
                    'signed_date': contract.user_signature_date,
                    'contract_html': contract.contract_html,
                    'name': contract.name,
                })
                emails = [contract.user.email, settings.DEFAULT_FROM_EMAIL] + \
                         [user.email for user in CapUser.objects.filter(groups__name='contract_approvers')]
                subject = 'CAP Bulk Access Agreement for {} {}'.format(contract.user.first_name, contract.user.last_name)
                msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, emails)
                msg.content_subtype = "html"  # Main content is text/html
                msg.send()

                # send welcome email
                message = loader.get_template('research_request/emails/contract_welcome_email.html').render({
                    'contact_url': reverse('contact', scheme='https'),
                })
                send_mail('Your CAP unrestricted access application is approved!', message, settings.DEFAULT_FROM_EMAIL, [contract.user.email])

                # show status message
                approver_message = "Research access for %s approved" % contract.name

        elif request.POST.get('deny') == "true":
            # update contract
            contract.status = 'denied'
            contract.save()

            # send notice email
            message = loader.get_template('research_request/emails/contract_denied_email.html').render({
                'name': contract.name,
            })
            emails = [contract.user.email, settings.DEFAULT_FROM_EMAIL] + \
                     [user.email for user in CapUser.objects.filter(groups__name='contract_approvers')]
            subject = 'CAP unrestricted access application denied for {} {}'.format(contract.user.first_name,
                                                                                 contract.user.last_name)
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails)

            # show status message
            approver_message = "Research access for %s denied" % contract.name
        else:
            pass  # we don't save if somehow approve or deny wasn't submitted

    contracts = ResearchContract.objects.filter(status='pending')
    return render(request, 'research_request/approve.html', {'contracts': contracts, 'approver_message': approver_message})


def bulk(request):
    """ List zips available for download """
    query = CaseExport.objects.exclude_old().order_by('body_format')

    # only show private downloads to logged in users
    if not request.user.unlimited_access_in_effect():
        query = query.filter(public=True)

    # sort exports by filter_type, filter_item, body_format so various levels are consistently sorted
    exports = list(query)
    CaseExport.load_filter_items(exports)
    exports.sort(key=lambda x: (x.filter_type, str(x.filter_item), x.body_format))

    # group exports into the hierarchy they'll appear on the page, making a dictionary like:
    # sorted_exports = {
    #   'public': {
    #       'jurisdiction': {
    #           <Jurisdiction>: {'xml': <CaseExport>, 'text': <CaseExport>},
    #       },
    #       'reporter': <ditto>
    #   'private: { <ditto> }
    # }
    sorted_exports = {}
    for export in exports:
        sorted_exports\
            .setdefault('public' if export.public else 'private', OrderedDict())\
            .setdefault(export.filter_type, OrderedDict())\
            .setdefault(export.filter_item, OrderedDict()) \
            [export.body_format] = export

    return render(request, 'bulk.html', {
        'exports': sorted_exports,
    })

@login_required()
def reset_api_key(request):
    """
        If it's a GET request, it will return the reset_api_key instructions/warnings/confirmation type page.
        If it's a POST request, it will reset the API key, and send out a confirmation email.
    """
    if request.method == 'POST' and request.user.is_active and request.user.email_verified:

        request.user.reset_api_key()
        request.user.save()

        message = ("Dear {} {},\nYour Case.law API key reset is complete. Your old key will no longer work; this cannot"
        " be undone. If you did not initiate this change, please reset your password and contact us, immediately."
        ".\n\nWarmest Regards,\nThe Caselaw Access Project Team\nHarvard Law "
        "School Library Innovation Lab")

        send_mail(
            'Case.law: API Key Reset for {} {}'.format(request.user.first_name, request.user.last_name),
            message.format(request.user.first_name, request.user.last_name),
            settings.DEFAULT_FROM_EMAIL, # from email
            [ settings.DEFAULT_FROM_EMAIL, request.user.email ], #to email, (sends a copy to us)
            fail_silently=False
        )
        return redirect('user-details')
    return render(request, 'registration/reset_api_key.html')


@login_required()
def delete_account(request):
    if request.method == 'POST':
        request.user.is_active = False
        request.user.deactivated_by_user = True
        request.user.save()
        return HttpResponseRedirect(reverse('home'))

    return render(request, 'registration/delete_account.html')
