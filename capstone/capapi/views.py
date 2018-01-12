from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from django.utils.decorators import decorator_from_middleware
from django.shortcuts import render

from rest_framework import status
from rest_framework import renderers, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import api_view, list_route, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.exceptions import ValidationError

from capapi import permissions, serializers, filters, resources, models as capapi_models
from capapi.middleware import RequestLogMiddleware
from capdb import models


class BaseViewMixin(viewsets.GenericViewSet):

    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super(BaseViewMixin, cls).as_view(*args, **kwargs)
        return decorator_from_middleware(RequestLogMiddleware)(view)


class JurisdictionViewSet(BaseViewMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.JurisdictionSerializer
    http_method_names = ['get']
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.JurisdictionFilter
    queryset = models.Jurisdiction.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    lookup_field = 'slug'


class VolumeViewSet(BaseViewMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.VolumeSerializer
    http_method_names = ['get']
    queryset = models.VolumeMetadata.objects.all().select_related(
        'reporter'
    ).prefetch_related('reporter__jurisdictions')
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class ReporterViewSet(BaseViewMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.ReporterSerializer
    http_method_names = ['get']
    queryset = models.Reporter.objects.all().prefetch_related('jurisdictions')
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CourtViewSet(BaseViewMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.CourtSerializer
    http_method_names = ['get']
    filter_class = filters.CourtFilter
    queryset = models.Court.objects.all().select_related('jurisdiction')
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    lookup_field = 'slug'


class CitationViewSet(BaseViewMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.CitationSerializer
    http_method_names = ['get']
    queryset = models.Citation.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CaseViewSet(BaseViewMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.CaseSerializer
    http_method_names = ['get']
    queryset = models.CaseMetadata.objects.all().select_related(
        'jurisdiction',
        'court',
        'volume',
        'reporter',
    ).prefetch_related('citations')
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    permission_classes = (permissions.IsAPIUser,)
    filter_class = filters.CaseFilter
    lookup_field = 'slug'
    order_by = 'decision_date'

    def download(self, **kwargs):
        if kwargs.get(self.lookup_field):
            try:
                case_list = [models.CaseMetadata.objects.get(**kwargs)]
            except models.CaseMetadata.DoesNotExist as e:
                return JsonResponse({
                    'message': 'Unable to find case with matching slug: %s' % e
                }, status=404, )

        else:
            cases = self.queryset.all()
            for backend in list(self.filter_backends):
                cases = backend().filter_queryset(self.request, cases, self)

            # user is requesting a zip but there is nothing to zip, so 404 is the right response.
            # See https://stackoverflow.com/a/11760249/307769
            if not cases.exists():
                return JsonResponse({
                    'message': 'Request did not return any results.',
                }, status=404, )

            case_list = self.paginate_queryset(cases)

        blacklisted_case_count = len(list((case for case in case_list if not case.jurisdiction.whitelisted)))

        try:
            # check user's case allowance against blacklisted
            user = serializers.UserSerializer().verify_case_allowance(self.request.user, blacklisted_case_count)
        except ValidationError as err:
            return JsonResponse(err.detail, status=403)

        filename = resources.create_zip_filename(case_list)

        case_response = serializers.CaseSerializerWithCasebody(case_list, many=True, context={'request': self.request})
        case_data = case_response.data
        response = resources.create_download_response(filename=filename, content=case_data)
        user.update_case_allowance(case_count=blacklisted_case_count)

        return response

    def list(self, *args, **kwargs):
        if not self.request.query_params.get('type') == 'download':
            return super(CaseViewSet, self).list(*args, **kwargs)
        else:
            return self.download(**kwargs)

    def retrieve(self, *args, **kwargs):
        if not self.request.query_params.get('type') == 'download':
            return super(CaseViewSet, self).retrieve(*args, **kwargs)
        else:
            return self.download(**kwargs)


# User specific views
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

                    return Response({
                        'email': user.email,
                        'api_key': user.get_api_key(),
                        'case_allowance_remaining': user.case_allowance_remaining,
                        'total_case_allowance': user.total_case_allowance
                    }, template_name='user-account.html',)
                else:
                    return Response({'user_id': user.id, 'user_email': user.email, 'info_email': settings.EMAIL_ADDRESS}, template_name='resend-nonce.html', )
            except Exception:
                content = {'errors': {'messages': 'Invalid password or email address'}, 'serializer': serializer}
                return Response(content, template_name='log-in.html', status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'errors': serializer.errors, 'serializer': serializer}, template_name='log-in.html', status=status.HTTP_401_UNAUTHORIZED)

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


def get_docs(request):
    case = models.CaseMetadata.objects.last()
    reporter = models.Reporter.objects.last()
    reporter_metadata = serializers.ReporterSerializer(reporter, context={'request': request}).data
    case_metadata = serializers.CaseSerializer(case, context={'request': request}).data
    context = {
        "case_metadata": case_metadata,
        "case_slug": case_metadata['slug'],
        "case_jurisdiction": case_metadata['jurisdiction'],
        "reporter_id": reporter_metadata['id'],
        "reporter_metadata": reporter_metadata,
    }
    return render(request, 'docs.html', context)
