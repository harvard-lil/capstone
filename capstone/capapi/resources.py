import json
from datetime import datetime
import logging
import zipfile
import tempfile
from wsgiref.util import FileWrapper
import wrapt

from django.conf import settings
from django.core.mail import send_mail
from django.template.defaultfilters import slugify
from django.http import FileResponse
from rest_framework.reverse import reverse

logger = logging.getLogger(__name__)


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

    response = FileResponse(FileWrapper(tmp_file), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


def send_new_signup_email(request, user):
    token_url = reverse('verify-user', kwargs={'user_id':user.pk, 'activation_nonce': user.get_activation_nonce()}, request=request)
    send_mail(
        'CaseLaw Access Project: Verify your email address',
        "Please click here to verify your email address: \n\n%s \n\nIf you believe you have received this message in error, please ignore it." % token_url,
        settings.API_EMAIL_ADDRESS,
        [user.email],
        fail_silently=False, )
    logger.info("sent new_signup email for %s" % user.email)


def form_for_request(request, FormClass):
    """ return FormClass loaded with request.POST data, if any """
    return FormClass(request.POST if request.method == 'POST' else None)


class TrackingWrapper(wrapt.ObjectProxy):
    """
        Object wrapper that stores all accessed attributes of underlying object in _self_accessed_attrs. Example:

            user = CapUser.objects.get(pk=1)
            user = TrackingWrapper(user)
            print(user.id)
            assert user._self_accessed_attrs == {'id'}
    """
    def __init__(self, wrapped):
        super().__init__(wrapped)
        self._self_accessed_attrs = set()

    def __getattr__(self, item):
        self._self_accessed_attrs.add(item)
        return super().__getattr__(item)