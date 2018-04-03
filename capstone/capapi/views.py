import urllib
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.decorators import decorator_from_middleware
from django.utils.text import slugify
from django.shortcuts import render

from rest_framework import status
from rest_framework import renderers, viewsets, mixins
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.decorators import api_view, list_route, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser

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
    serializer_class = serializers.CitationWithCaseSerializer
    http_method_names = ['get']
    queryset = models.Citation.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CaseViewSet(BaseViewMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.CaseSerializer
    http_method_names = ['get']
    queryset = models.CaseMetadata.objects.exclude(
        duplicative=True).select_related(
        'volume',
        'reporter',
        ).prefetch_related(
        'citations'
        ).select_related(
        'jurisdiction',
        'court'
        ).filter(jurisdiction__isnull=False, court__isnull=False)

    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    filter_class = filters.CaseFilter
    lookup_field = 'id'

    def get_serializer_class(self, *args, **kwargs):
        full_case = self.request.query_params.get('full_case', 'false').lower()
        if full_case == 'true':
            return serializers.CaseSerializerWithCasebody
        else:
            return self.serializer_class

    def retrieve(self, *args, **kwargs):
        # for user's convenience, if user gets /cases/case-citation or /cases/Case Citation
        # we redirect to /cases/?cite=case-citation
        if kwargs.get(self.lookup_field, None):
            slugified = slugify(kwargs[self.lookup_field])
            if '-' in slugified:
                query_string = urllib.parse.urlencode(dict(self.request.query_params, cite=slugified), doseq=True)
                new_url = reverse('casemetadata-list') + "?" + query_string
                return HttpResponseRedirect(new_url)

        queryset = super(CaseViewSet, self).retrieve(*args, **kwargs)

        return queryset


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

    @list_route(methods=['post'], permission_classes=[permissions.IsAuthenticatedAPIUser])
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
    if user.is_authenticated:
        resources.email(reason='new_registration', user=user)
        data = {'status': 'Success!', 'message': 'Thank you for verifying your email address. We will be in touch with you shortly.'}
        if request.accepted_renderer.format == 'json':
            return JsonResponse(data)
        return Response(data, template_name='verified.html')
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


def get_docs(request):
    case = models.CaseMetadata.objects.get(id=settings.API_DOCS_CASE_ID)
    reporter = case.reporter
    reporter_metadata = serializers.ReporterSerializer(reporter, context={'request': request}).data
    case_metadata = serializers.CaseSerializer(case, context={'request': request}).data
    whitelisted_jurisdictions = models.Jurisdiction.objects.filter(whitelisted=True).values('name_long', 'name')

    context = {
        "template_name": 'docs',
        "case_metadata": case_metadata,
        "case_id": case_metadata['id'],
        "case_jurisdiction": case_metadata['jurisdiction'],
        "reporter_id": reporter_metadata['id'],
        "reporter_metadata": reporter_metadata,
        "whitelisted_jurisdictions": whitelisted_jurisdictions,
    }

    return render(request, 'docs.html', context)


def get_terms(request):
    context = {"template_name": 'terms'}
    return render(request, 'terms-of-use.html', context)


def not_found(request):
    return render(request, '404.html')
