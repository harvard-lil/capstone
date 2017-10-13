import os
import logging
from wsgiref.util import FileWrapper

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse, StreamingHttpResponse

from rest_framework import status
from rest_framework import renderers, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import api_view, list_route, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser

from capapi import view_helpers, permissions, serializers, filters, resources, models as capapi_models
from capapi.constants import OPEN_CASE_JURISDICTIONS
from capdb import models



logger = logging.getLogger(__name__)


class JurisdictionViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.JurisdictionSerializer
    http_method_names = ['get']
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.JurisdictionFilter
    queryset = models.Jurisdiction.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class VolumeViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.VolumeSerializer
    http_method_names = ['get']
    queryset = models.VolumeMetadata.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class ReporterViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.ReporterSerializer
    http_method_names = ['get']
    queryset = models.Reporter.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CourtViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.CourtSerializer
    http_method_names = ['get']
    queryset = models.Court.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CitationViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.CitationSerializer
    http_method_names = ['get']
    queryset = models.Citation.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CaseViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.CaseSerializer
    http_method_names = ['get']
    lookup_field = 'slug'
    queryset = models.CaseMetadata.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    permission_classes = (permissions.IsAPIUser,)
    filter_class = filters.CaseFilter

    def download_many(self):
        all_cases = self.queryset.all()
        # get max number of cases to download from query
        # set max number to daily max if unspecified
        max_num = int(self.request.query_params.get('max', settings.API_CASE_DAILY_ALLOWANCE))

        try:
            to_filter = view_helpers.generate_filters_from_query_params(self.request.query_params)
            cases = all_cases.filter(to_filter).order_by('decision_date')
        except TypeError:
            cases = all_cases.order_by('decision_date')

        if cases.count() == 0:
            return JsonResponse({
                'message': 'Request did not return any results.'
            }, status=404, )

        # get page number for paginated requests
        page_num = int(self.request.query_params.get('page', 1))

        # pagination or max number
        if max_num <= settings.API_DOWNLOAD_LIMIT:
            cases = cases[:max_num]
        else:
            start_at = (page_num-1) * settings.API_DOWNLOAD_LIMIT
            end_at = page_num * settings.API_DOWNLOAD_LIMIT
            cases = cases[start_at:end_at]

        # if request was already paginated
        whitelisted_filters = view_helpers.get_whitelisted_case_filters()
        blacklisted_case_count = len(set(cases) & set(all_cases.exclude(whitelisted_filters)))

        case_allowance_sufficient = self.check_case_allowance(blacklisted_case_count)
        return self.create_download_response(list(cases), blacklisted_case_count, permitted=case_allowance_sufficient)

    def download_one(self, **kwargs):
        """
        If downloading a single case (using its lookup_field) explicitly
        """
        lookup_field = CaseViewSet.lookup_field
        try:
            case = models.CaseMetadata.objects.get(**{lookup_field: kwargs.get(lookup_field, None)})
        except ObjectDoesNotExist as e:
            return JsonResponse({'message': 'Unable to find case with matching slug: %s' % e}, status=404, )

        blacklisted_case_count = 0 if case.jurisdiction.name in OPEN_CASE_JURISDICTIONS else 1
        case_allowance_sufficient = self.check_case_allowance(blacklisted_case_count)

        return self.create_download_response([case], blacklisted_case_count, permitted=case_allowance_sufficient)

    def create_download_response(self, case_list, blacklisted_case_count, permitted=False):
        if permitted:
            try:
                zip_filename = self.get_zip_filename(case_list)
                self.request.user.case_allowance -= blacklisted_case_count
                self.request.user.save()
                response = StreamingHttpResponse(FileWrapper(open(zip_filename, 'rb')), content_type='application/zip')
                response['Content-Length'] = os.path.getsize(zip_filename)
                response['Content-Disposition'] = 'attachment; filename="%s"' % zip_filename
                return response
            except Exception as e:
                return JsonResponse({'message': 'Download file error: %s' % e}, status=403, )
        else:
            case_allowance = self.request.user.case_allowance
            time_remaining = self.request.user.get_case_allowance_update_time_remaining()
            message = "You have reached your limit of allowed cases. Your limit will reset to default again in %s", time_remaining
            details = """
                      You attempted to download %s cases and your current remaining case limit is %s. 
                      Use the max flag to return a specific number of cases: &max=%s
                      """ % (
                blacklisted_case_count,
                case_allowance,
                case_allowance
            )

            return JsonResponse({'message': message, 'details': details}, status=403)

    def check_case_allowance(self, case_count):
        if case_count <= 0:
            return True
        self.request.user.update_case_allowance()
        return self.request.user.case_allowance >= case_count

    def list(self, *args, **kwargs):
        if not self.request.query_params.get('type') == 'download':
            return super(CaseViewSet, self).list(*args, **kwargs)
        else:
            return self.download_many()

    def retrieve(self, *args, **kwargs):
        if not self.request.query_params.get('type') == 'download':
            return super(CaseViewSet, self).retrieve(*args, **kwargs)
        else:
            return self.download_one(**kwargs)

    def get_zip_filename(self, caselist):
        try:
            return resources.write_and_zip(caselist)
        except Exception as e:
            raise Exception("Download cases error %s" % e)


#   User specific views
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserSerializer
    renderer_classes = [renderers.TemplateHTMLRenderer]
    queryset = capapi_models.APIUser.objects.all()
    parser_classes = (JSONParser, FormParser,)
    lookup_field = 'email'

    @list_route(methods=['get'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = serializers.RegisterUserSerializer()

        return Response({'serializer': serializer}, template_name='sign-up.html')

    @list_route(methods=['post'], permission_classes=[AllowAny])
    def register_user(self, request):
        serializer = serializers.RegisterUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.create({
                'email': request.data.get('email'),
                'password': request.data.get('password'),
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name')
            })
            content = {
                'status': 'Success!',
                'message': 'Thank you. Please check your email %s for a verification link.' % user.email
            }
            return Response(content, template_name='sign-up-success.html')
        else:
            return Response({'serializer': serializer, 'errors': serializer.errors}, template_name='sign-up.html', status=status.HTTP_400_BAD_REQUEST)

    @list_route(methods=['get'], permission_classes=[AllowAny])
    def login(self, request):
        serializer = serializers.LoginSerializer()
        return Response({'serializer': serializer}, template_name='log-in.html')

    @list_route(methods=['post'], permission_classes=[AllowAny])
    def view_details(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.verify_with_password(email=request.data.get('email'), password=request.data.get('password'))

                api_key = user.get_api_key()
                if api_key:
                    # update case allowance before sending back
                    user.update_case_allowance()
                    user.refresh_from_db()

                    return Response({'email': user.email, 'api_key': user.get_api_key(), 'case_allowance': user.case_allowance}, template_name='user-account.html',)
                else:
                    return Response({'user_id': user.id, 'user_email': user.email, 'info_email': settings.EMAIL_ADDRESS}, template_name='resend-nonce.html', )
            except Exception:
                content = {'errors': {'messages': 'Invalid password or email address'}, 'serializer': serializer}
                return Response(content, template_name='log-in.html', status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'errors': serializer.errors, 'serializer': serializer}, template_name='log-in.html', status=status.HTTP_400_BAD_REQUEST)

    @list_route(methods=['post'], permission_classes=[permissions.IsAPIUser])
    def resend_verification(self, request):

        user = capapi_models.APIUser.objects.get(email=request.data.get('user_email'))

        resources.email(reason='new_signup', user=user)
        content = {
            'status': 'Success!',
            'message': 'Thank you. Please check your email %s for a verification link.' % user.email
        }
        return Response(content, template_name='sign-up-success.html')


@api_view(http_method_names=['GET'])
@renderer_classes((renderers.TemplateHTMLRenderer, renderers.JSONRenderer,))
def verify_user(request, user_id, activation_nonce):
    """
    Verify email and assign api token
    """
    serializer = serializers.UserSerializer()
    user = serializer.verify_with_nonce(user_id, activation_nonce)
    if user.is_authenticated():
        resources.email(reason='new_registration', user=user)
        data = {'status': 'Success!', 'message': 'Thank you for verifying your email address. We will be in touch with you shortly.'}
        if request.accepted_renderer.format == 'json':
            return JsonResponse(data)
        return Response(data, template_name='verified.html')
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
