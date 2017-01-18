import os
import csv
import paramiko

from django.conf import settings
from django.core.mail import send_mail

from capi_project.models import Case
from scp import SCPClient
from datetime import datetime
from django.template.defaultfilters import slugify

def get_formatted_date():
    return slugify(str(datetime.today()))

def format_filename(case_id):
    cdir, cpgnumber = case_id.split('_')
    cdirname = cdir + '_redacted'
    return settings.CAP_DATA_DIR_VAR + '/' + cdirname+'/casemets/' + cdirname + '_CASEMETS_' + cpgnumber + settings.CASE_FILE_TYPE

def format_filename_whitelisted(case_id):
    cdir, cpgnumber = case_id.split('_')
    cdirname = cdir + '_redacted'
    return settings.WHITELISTED_DATA_DIR + '/' + cdirname+'/casemets/' + cdirname + '_CASEMETS_' + cpgnumber + settings.CASE_FILE_TYPE

def download_blacklisted(requester_id, list_of_files):
    try:
        ssh = paramiko.SSHClient()
        list_of_files = map(format_filename, list_of_files)
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(settings.PRIVATE_KEY_FILENAME)
        ssh.connect(settings.CAP_SERVER_TO_CONNECT_TO, port=22, pkey=private_key, username='capuser')
        string_list = str(list_of_files)
        zip_filename = "cases_%s_%s.zip" % (requester_id, get_formatted_date())
        ssh.exec_command("touch %s" % zip_filename)
        print("creating %s" % zip_filename)
        stdin, stdout, stderr = ssh.exec_command('python cap_api_gzip_cases.py %s \"%s\"' % (zip_filename, string_list))
        if stderr.read():
            raise Exception('Uh Oh! Something went wrong')
        scp_client = SCPClient(ssh.get_transport())
        scp_client.get("%s" % zip_filename)
        print('downloading %s' % zip_filename)
        scp_client.close()
        move_casezip(zip_filename)
        return zip_filename

    except Exception as e:
        print("Error on case download: %s" % e)

def download_whitelisted(requester_id, list_of_files):
    list_of_files = map(format_filename_whitelisted, list_of_files)
    zip_filename = "cases_%s_%s.zip" % (requester_id, get_formatted_date())
    gzip_documents(zip_filename, list_of_files)
    move_casezip(zip_filename)
    return zip_filename

def gzip_documents(zipname, filenames):
    import zipfile
    try:
        import zlib
        compression = zipfile.zip_deflated
    except:
        compression = zipfile.ZIP_STORED

    with zipfile.ZipFile(zipname, 'w') as zapfile:
        for f in filenames:
            fname = f.split('/')[-1]
            zapfile.write(f, fname, compress_type=zipfile.ZIP_DEFLATED)

        return zapfile

def move_casezip(filename):
    new_dest = "%s/%s" % (settings.CASE_ZIP_DIR, filename)
    os.rename(filename, new_dest)

def email(reason, user):
    title = 'CAP API: %s' % reason
    if reason == 'new_registration':
        message = "user %s %s at %s has requested API access." % (user.first_name, user.last_name, user.email)
        send_mail(title, message, settings.ADMIN_EMAIL_ADDRESS, [settings.EMAIL_ADDRESS])
        print "sent new_registration email for %s" % user.email

    if reason == 'new_signup':
        token_url= "%saccounts/verify-user/%s/%s" % (settings.BASE_URL, user.id, user.get_activation_nonce())
        send_mail(
            'CaseLaw Access Project: Verify your email address',
            """
                Please click here to verify your email address: %s
            """ % token_url,
            settings.EMAIL_ADDRESS,
            [user.email],
            fail_silently=False,)
        print "sent new_signup email for %s" % user.email


if __name__ == '__main___':
    create_metadata_from_csv()
