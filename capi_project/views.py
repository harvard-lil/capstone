from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Q
from django.db import IntegrityError
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, renderers, routers, viewsets, views, mixins, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, detail_route, list_route, permission_classes, renderer_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

from .models import Case
from .view_helpers import *
from .serializers import *
from .permissions import IsCaseUser, IsAdmin
from .filters import *
from .case_views import *
from .resources import email

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = renderers.JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    renderer_classes = [renderers.TemplateHTMLRenderer]
    queryset = CaseUser.objects.all()
    parser_classes = (JSONParser, FormParser,)
    lookup_field = 'email'

    @list_route(methods=['get'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = RegisterUserSerializer()
        return Response({'serializer':serializer}, template_name='sign-up.html')

    @list_route(methods=['post'], permission_classes=[AllowAny])
    def register_user(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.create({
                    'email':request.data.get('email'),
                    'password':request.data.get('password')
                    })
                content = {
                'status':'Success!',
                'message':'Thank you. Please check your email %s for a verification link.' % user.email}

                return Response(content, template_name='sign-up-success.html')

            except IntegrityError:
                return Response({'errors':serializer.errors}, template_name='sign-up-success.html', status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'serializer':serializer, 'errors':serializer.errors}, template_name='sign-up-success.html', status=status.HTTP_400_BAD_REQUEST)

    @list_route(methods=['get'], permission_classes=[AllowAny])
    def login(self, request):
        serializer = LoginSerializer()
        return Response({'serializer':serializer}, template_name='log-in.html')

    @list_route(methods=['post'], permission_classes=[AllowAny])
    def view_details(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.verify_with_password(email=request.data.get('email'), password=request.data.get('password'))
                return Response({'email':user.email, 'api_key':user.get_api_key}, template_name='token.html',)
            except Exception as e:
                print e
                return Response({'errors':e}, template_name='token.html', status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'errors':serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(http_method_names=['GET'])
@renderer_classes((renderers.BrowsableAPIRenderer,renderers.JSONRenderer,))
def verify_user(request, user_id, activation_nonce):
    """
    Verify email and assign api token
    """
    serializer = UserSerializer()
    user = serializer.verify_with_nonce(user_id, activation_nonce)
    if user.is_authenticated():
        data = {'status':'Success!','message':'Thank you for verifying your email address. We will be in touch with you shortly.'}
        if request.accepted_renderer.format == 'html' :
            return Response(data, template_name='verified.html')
        elif request.accepted_renderer.format == 'api' :
            return Response(data)
        else:
            return JSONResponse(data)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(http_method_names=['GET','POST'])
@parser_classes((FormParser, MultiPartParser, JSONParser,))
@renderer_classes((renderers.BrowsableAPIRenderer, renderers.TemplateHTMLRenderer, renderers.JSONRenderer, ))
def get_token(request):
    serializer = LoginSerializer()
    if request.method == 'GET':
        return Response({'serializer':serializer}, template_name='get-token.html')
    elif request.method == 'POST':
        try:
            email = request.data.get('email')
            password = request.data.get('password')
            user = serializer.verify_with_password(email, password)
            if user.is_validated:
                api_key = user.get_api_key()
                data = {'email':user.email,'api_key':api_key, 'case_allowance':user.case_allowance}
                if request.accepted_renderer.format != 'json' :
                    return Response(data, template_name='user-account.html')
                else:
                    return JSONResponse(data)
        except Exception as e:
            data = {'status':'Failed.','message':'Please check that your entered credentials are correct.'}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
