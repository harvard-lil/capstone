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
                                                    settings.CASE_FILE_TYPE)


def download_blacklisted(requester_id, list_of_files):
    list_of_files = map(format_filename, list_of_files)
    string_list = str(list_of_files)
    zip_filename = "cases_%s_%s.zip" % (requester_id, get_formatted_date())

    if not settings.DEBUG:
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(
            settings.PRIVATE_KEY_FILENAME)
        ssh.connect(
            settings.CAP_SERVER_TO_CONNECT_TO,
            port=22,
            pkey=private_key,
            username='capuser'
        )
        ssh.exec_command("touch %s" % zip_filename)
        logger.info("creating %s" % zip_filename)
        stdin, stdout, stderr = ssh.exec_command(
            'python cap_api_gzip_cases.py %s \"%s\"' % (
                zip_filename, string_list
            )
        )
        if stderr.read():
            raise Exception('Uh Oh! Something went wrong: %s', stderr.read())
        scp_client = SCPClient(ssh.get_transport())
        scp_client.get("%s" % zip_filename)
        logger.info("downloading %s" % zip_filename)
        scp_client.close()
        move_casezip(zip_filename)

    return zip_filename


def download_whitelisted(requester_id, list_of_files):
    list_of_files = [format_filename(f, whitelisted=True) for f in list_of_files]
    zip_filename = "cases_%s_%s.zip" % (requester_id, get_formatted_date())
    gzip_documents(zip_filename, list_of_files)
    move_casezip(zip_filename)
    return zip_filename


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
            settings.ADMIN_EMAIL_ADDRESS,
            [settings.EMAIL_ADDRESS]
        )
        logger.info("sent new_registration email for %s" % user.email)

    if reason == 'new_signup':
        token_url = "%saccounts/verify-user/%s/%s" % (
            settings.BASE_URL, user.id, user.get_activation_nonce()
        )
        send_mail(
            'CaseLaw Access Project: Verify your email address',
            """
                Please click here to verify your email address: %s
            """ % token_url,
            settings.EMAIL_ADDRESS,
            [user.email],
            fail_silently=False, )
        logger.info("sent new_signup email for %s" % user.email)
