import logging

from django.http import HttpResponse
from django.db import IntegrityError

from rest_framework import status, renderers, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, list_route, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser

from . import models, serializers, resources, permissions, settings

logger = logging.getLogger(__name__)


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = renderers.JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserSerializer
    renderer_classes = [renderers.TemplateHTMLRenderer]
    queryset = models.CaseUser.objects.all()
    parser_classes = (JSONParser, FormParser,)
    lookup_field = 'email'

    @list_route(methods=['get'], permission_classes=[AllowAny])
    def register(self):
        serializer = serializers.RegisterUserSerializer()
        return Response({'serializer': serializer}, template_name='sign-up.html')

    @list_route(methods=['post'], permission_classes=[AllowAny])
    def register_user(self, request):
        serializer = serializers.RegisterUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
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
            except IntegrityError as e:
                logger.error('IntegrityError %s %s %s' % (e, dir(e), request.data.get('email')))
                content = {
                    'status': 'Error',
                    'message': "IntegrityError",
                    'errors': e
                }
                return Response(content, template_name='sign-up-success.html', status=status.HTTP_400_BAD_REQUEST)
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
                    user = models.CaseUser.objects.get(email=user.email)
                    return Response({'email': user.email, 'api_key': user.get_api_key(), 'case_allowance': user.case_allowance}, template_name='user-account.html',)
                else:
                    return Response({'user_id': user.id, 'user_email': user.email, 'info_email': settings.EMAIL_ADDRESS}, template_name='resend-nonce.html', )
            except Exception:
                content = {'errors': {'messages': 'Invalid password or email address'}, 'serializer': serializer}
                return Response(content, template_name='log-in.html', status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'errors': serializer.errors, 'serializer': serializer}, template_name='log-in.html', status=status.HTTP_400_BAD_REQUEST)

    @list_route(methods=['post'], permission_classes=[permissions.IsCaseUser])
    def resend_verification(self, request):

        user = models.CaseUser.objects.get(email=request.data.get('user_email'))
        if str(user.id) == request.data.get('user_id'):

            resources.email(reason='new_signup', user=user)
            content = {
                'status': 'Success!',
                'message': 'Thank you. Please check your email %s for a verification link.' % user.email
            }
            return Response(content, template_name='sign-up-success.html')

        else:
            raise Exception("Attempted sending email with unmatched credentials %s %s" % (user.id, request.data.get('user_email')))
            return Response({'errors': 'Uh oh. Something went wrong.'}, template_name='errors.html', status=status.HTTP_400_BAD_REQUEST)


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
            return JSONResponse(data)
        return Response(data, template_name='verified.html')
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
