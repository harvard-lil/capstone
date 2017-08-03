import os
from datetime import datetime
import logging

import paramiko
from scp import SCPClient
from django.conf import settings
from django.core.mail import send_mail
from django.template.defaultfilters import slugify

logger = logging.getLogger(__name__)


def get_formatted_date():
    return slugify(str(datetime.today()))


def format_filename(case_id, whitelisted=False):
    cdir, cpgnumber = case_id.split('_')
    cdirname = cdir + '_redacted'
    data_dir = settings.CAP_DATA_DIR_VAR
    if whitelisted:
        data_dir = settings.WHITELISTED_DATA_DIR

    return "{}/{}/casemets/{}_CASEMETS_{}{}".format(data_dir,
                                                    cdirname,
                                                    cdirname,
                                                    cpgnumber,
                                                    settings.API_CASE_FILE_TYPE)


def gzip_documents(zipname, filenames):
    import zipfile
    try:
        compression = zipfile.zip_deflated
    except:
        compression = zipfile.ZIP_STORED

    with zipfile.ZipFile(zipname, 'w') as zapfile:
        for f in filenames:
            fname = f.split('/')[-1]
            zapfile.write(f, fname, compress_type=compression)

        return zapfile


def move_casezip(filename):
    new_dest = "%s/%s" % (settings.CASE_ZIP_DIR, filename)
    os.rename(filename, new_dest)


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
        token_url = "%saccounts/verify-user/%s/%s" % (
            settings.API_BASE_URL, user.id, user.get_activation_nonce()
        )
        send_mail(
            'CaseLaw Access Project: Verify your email address',
            """
                Please click here to verify your email address: %s
                If you believe you have received this message in error, please ignore it.
            """ % token_url,
            settings.API_EMAIL_ADDRESS,
            [user.email],
            fail_silently=False, )
        logger.info("sent new_signup email for %s" % user.email)
