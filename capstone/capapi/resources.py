import os
import json
from datetime import datetime
import logging
import zipfile
import tempfile
from wsgiref.util import FileWrapper

from django.conf import settings
from django.core.mail import send_mail
from django.template.defaultfilters import slugify
from django.http import FileResponse

from capdb.models import CaseXML

logger = logging.getLogger(__name__)


def get_matching_case_xml(case_id):
    try:
        xml = CaseXML.objects.get(case_id=case_id)
        return xml.orig_xml
    except CaseXML.DoesNotExist:
        logger.error("Case id mismatch", case_id)


def create_zip_filename(case_list):
    ts = slugify(datetime.now().timestamp())
    if len(case_list) == 1:
        return case_list[0].slug + '-' + ts + '.zip'

    return '{0}_{1}_{2}.zip'.format(case_list[0].slug[:20], case_list[-1].slug[:20], ts)


def create_download_response(filename='', content=[]):
    # tmp file backed by RAM up to 10MB, then stored to disk
    tmp_file = tempfile.SpooledTemporaryFile(10 * 2 ** 20)
    with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in content:
            archive.writestr(item['slug'] + '.json', json.dumps(item))

    # Reset file pointer
    tmp_file.seek(0)

    # return open file handle
    # return tmp_file
    response = FileResponse(FileWrapper(tmp_file), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


def email(reason, user):
    title = 'CAP API: %s' % reason
    if reason == 'new_registration':
        message = "user %s %s at %s has requested API access." % (
            user.first_name,
            user.last_name,
            user.email
        )
        send_mail(
            title,
            message,
            settings.API_ADMIN_EMAIL_ADDRESS,
            [settings.API_EMAIL_ADDRESS]
        )
        logger.info("sent new_registration email for %s" % user.email)

    if reason == 'new_signup':
        token_url = os.path.join(settings.API_BASE_URL, "accounts/verify-user", str(user.id), user.get_activation_nonce())
        send_mail(
            'CaseLaw Access Project: Verify your email address',
            f"Please click here to verify your email address: {token_url} If you believe you have received this message in error, please ignore it.",
            settings.API_EMAIL_ADDRESS,
            [user.email],
            fail_silently=False, )
        logger.info("sent new_signup email for %s" % user.email)

