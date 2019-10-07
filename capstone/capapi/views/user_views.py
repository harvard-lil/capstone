import os
from collections import OrderedDict

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail, EmailMessage
from django.db import transaction
from django.http import HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.utils import timezone
from django.utils.safestring import mark_safe

from wsgiref.util import FileWrapper

from capapi import resources
from capapi.forms import RegisterUserForm, ResendVerificationForm, ResearchContractForm, \
    HarvardContractForm, UnaffiliatedResearchRequestForm, ResearchRequestForm
from capapi.models import SiteLimits, CapUser, ResearchContract
from capapi.resources import form_for_request
from capdb.models import CaseExport
from capweb.helpers import reverse, send_contact_email, user_has_harvard_email, render_markdown



def register_user(request):
    """ Create new user """
    form = form_for_request(request, RegisterUserForm)

    if request.method == 'POST' and form.is_valid():
        form.save()
        resources.send_new_signup_email(request, form.instance)
        return render(request, 'registration/sign-up-success.html', {
            'status': 'Success!',
            'message': 'Thank you. Please check your email for a verification link.',
            'page_name': 'user-register-success'
        })

    return render(request, 'registration/register.html', {'form': form,
                                                          'page_name': 'user-register'})


def verify_user(request, user_id, activation_nonce):
    """ Verify email and assign api token """
    try:
        user = CapUser.objects.get(pk=user_id)
        user.authenticate_user(activation_nonce=activation_nonce)
    except (CapUser.DoesNotExist, PermissionDenied):
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
        'contact_email': settings.DEFAULT_FROM_EMAIL,
        'error': error,
        'page_name': 'user-verify'
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
        'page_name': 'user-resend-verification'
    })


@login_required
def user_details(request):
    """ Show user details """
    request.user.update_case_allowance()
    context = {
        'page_name': 'user-details',
        'research_contract': request.user.research_contracts.first(),
        'research_request': request.user.research_requests.first(),
        'NEW_RESEARCHER_FEATURE': settings.NEW_RESEARCHER_FEATURE,
    }
    return render(request, 'registration/user-details.html', context)


@login_required
@user_has_harvard_email()
def request_harvard_research_access_intro(request):
    """ Warning shown before Harvard access page """
    return render(request, 'research_request/harvard_research_request_intro.html')


@login_required
@user_has_harvard_email()
def request_harvard_research_access(request):
    """ Sign Harvard-email based contract """
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
        msg = EmailMessage('CAP Bulk Access Agreement', message, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL, request.user.email])
        msg.content_subtype = "html"  # Main content is text/html
        msg.send()

        return HttpResponseRedirect(reverse('harvard-research-request-success'))

    return render(request, 'research_request/harvard_research_request.html', {'form': form})


@login_required
def request_legacy_research_access(request):
    """ Submit request for unaffiliated research access """
    name = "%s %s" % (request.user.first_name, request.user.last_name)
    form = form_for_request(request, ResearchRequestForm, initial={'name': name, 'email': request.user.email})

    if request.method == 'POST' and form.is_valid():
        # save request object
        form.instance.user = request.user
        form.save()

        # send notice emails
        message = loader.get_template('research_request/emails/legacy_request_email.txt').render({
            'data': form.cleaned_data,
        })
        send_contact_email('CAP research scholar application', message, request.user.email)

        return HttpResponseRedirect(reverse('unaffiliated-research-request-success'))

    return render(request, 'research_request/unaffiliated_research_request.html', {
        'form': form,
        'NEW_RESEARCHER_FEATURE': settings.NEW_RESEARCHER_FEATURE,
    })


@login_required
def request_unaffiliated_research_access(request):
    """ Submit request for unaffiliated research access """
    name = "%s %s" % (request.user.first_name, request.user.last_name)
    form = form_for_request(request, UnaffiliatedResearchRequestForm, initial={'name': name, 'email': request.user.email})

    if request.method == 'POST' and form.is_valid():
        # save request object
        form.instance.user = request.user
        form.save()

        # send notice emails
        message = loader.get_template('research_request/emails/unaffiliated_request_email.txt').render({
            'data': form.cleaned_data,
        })
        send_contact_email('CAP independent research scholar application', message, request.user.email)

        return HttpResponseRedirect(reverse('unaffiliated-research-request-success'))

    return render(request, 'research_request/unaffiliated_research_request.html', {
        'form': form,
        'NEW_RESEARCHER_FEATURE': settings.NEW_RESEARCHER_FEATURE,
    })


@login_required
def request_affiliated_research_access(request):
    """ Sign academic/nonprofit based contract """
    name = "%s %s" % (request.user.first_name, request.user.last_name)
    form = form_for_request(request, ResearchContractForm, initial={'name': name, 'email': request.user.email})

    if request.method == 'POST' and form.is_valid():
        # save contract object
        form.instance.user = request.user
        form.instance.contract_html = loader.get_template('research_request/contracts/affiliated_rendered.html').render({
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
        send_mail('CAP research contract application', message, settings.DEFAULT_FROM_EMAIL, emails)

        return HttpResponseRedirect(reverse('affiliated-research-request-success'))

    return render(request, 'research_request/affiliated_research_request.html', {'form': form})


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
                msg = EmailMessage('CAP Bulk Access Agreement', message, settings.DEFAULT_FROM_EMAIL, emails)
                msg.content_subtype = "html"  # Main content is text/html
                msg.send()

                # send welcome email
                message = loader.get_template('research_request/emails/contract_welcome_email.html').render({
                    'contact_url': reverse('contact', scheme='https'),
                })
                send_mail('Your CAP unmetered access application is approved!', message, settings.DEFAULT_FROM_EMAIL, [contract.user.email])

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
            send_mail('Your CAP unmetered access application has been denied', message, settings.DEFAULT_FROM_EMAIL, emails)

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


class FileObject:
    name = ''
    path = ''
    isdir = False

    def __init__(self, name, path):
        self.name = name
        self.path = os.path.join(path, name)
        abs_path = os.path.join(settings.STORAGES['download_files_storage']['kwargs']['location'], self.path)
        self.isdir = os.path.isdir(abs_path)


def download_files(request, filepath=""):
    """
    If directory requested: show list of files inside dir
    If file requested: downloads file
    """
    storage_path = settings.STORAGES['download_files_storage']['kwargs']['location']
    absolute_path = os.path.join(storage_path, filepath)

    allow_downloads = "restricted" not in absolute_path or request.user.unlimited_access_in_effect()

    # file requested
    if os.path.isfile(absolute_path):
        if not allow_downloads:
            context = {
                "filename": filepath,
                "error": "If you believe you should have access to this file, "
                         "please <a href='https://caselaw.freshdesk.com/support/tickets/new'>let us know</a>.",
                "title": "403 - Access to this file is restricted",
            }
            return render(request, "file_download_400.html", context, status=403)
        import magic
        mime = magic.Magic(mime=True)
        content_type = mime.from_file(absolute_path)
        chunk_size = 8192

        response = StreamingHttpResponse(FileWrapper(open(absolute_path, 'rb'), chunk_size), content_type=content_type)
        response['Content-Length'] = os.path.getsize(absolute_path)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filepath.split('/')[-1]

        return response

    # directory requested
    elif os.path.isdir(absolute_path):

        # create clickable breadcrumbs
        breadcrumb_parts = filepath.split('/')

        breadcrumbs = []
        for idx, breadcrumb in enumerate(breadcrumb_parts):
            if breadcrumb:
                breadcrumbs.append({'name': breadcrumb,
                                    'path': "/".join(breadcrumb_parts[0:idx + 1])})

        readme = ""
        files = []
        for filename in os.listdir(absolute_path):
            if filename == "README.md":
                with open(os.path.join(absolute_path, filename), "r") as f:
                    readme_content = f.read()
                readme, toc, meta = render_markdown(readme_content)

            fileobject = FileObject(name=filename, path=filepath)
            files.append(fileobject)

        context = {
            'files': files,
            'allow_downloads': allow_downloads
        }

        if len(breadcrumbs) > 0:
            context['breadcrumbs'] = breadcrumbs
        if readme:
            context['readme'] = mark_safe(readme)

        return render(request, "file_download.html", context)

    # path does not exist
    else:
        context = {
            "title": "404 - File not found",
            "error": "This file was not found in our system."
        }
        return render(request, "file_download_400.html", context, status=404)


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
            'Case.law: API Key Reset',
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