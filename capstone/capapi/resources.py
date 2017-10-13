import os
from datetime import datetime
import logging
import zipfile

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.mail import send_mail
from django.template.defaultfilters import slugify

from capdb.models import CaseXML

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


def write_and_zip(case_list):
    def get_matching_case_xml(case_id):
        try:
            xml = CaseXML.objects.get(case_id=case_id)
            return xml.orig_xml
        except ObjectDoesNotExist:
            logger.error("Case id mismatch", case_id)

    case_xml_tuples = [(case.slug, get_matching_case_xml(case.case_id)) for case in case_list]


    dirname = "{0}_{1}_{2}".format(
        case_list[0].slug,
        case_list[len(case_list)-1].slug,
        slugify(datetime.now().timestamp())
    )
    dirpath = settings.API_ZIPFILE_DIR + "/" + dirname

    try:
        compression = zipfile.zip_deflated
    except AttributeError:
        compression = zipfile.ZIP_STORED

    os.makedirs(dirpath)

    # write all files to dir
    [write_to_file("%s/%s.xml" % (dirpath, case_tuple[0]), case_tuple[1]) for case_tuple in list(case_xml_tuples)]

    # zip newly created directory
    zipped_dir = dirpath + ".zip"
    zipfile_handler = zipfile.ZipFile(zipped_dir, 'w', compression)
    zipdir('tmp/', zipfile_handler)
    zipfile_handler.close()

    return zipped_dir


def zipdir(path, zipfile_handler):
    for root, dirs, files in os.walk(path):
        for file in files:
            zipfile_handler.write(os.path.join(root, file))


def write_to_file(filename, xml):
    with open(filename, "w+") as f:
        f.write(xml)
    return filename


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
