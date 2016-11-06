from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import renderers
from django.http import HttpResponse

from django.db.models import Q

from rest_framework import routers, viewsets, views, mixins, permissions
from rest_framework.response import Response

from rest_framework.decorators import api_view, detail_route, list_route, permission_classes, renderer_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from .models import Case
from .view_helpers import *
from .serializers import *
from .permissions import IsCaseUser
from .filters import *
from .forms import SignupForm

from .case_views import *

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
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    queryset = CaseUser.objects.all()
    parser_classes = (JSONParser, FormParser,)
    lookup_field = 'email'
    def list(self, request, *args, **kwargs):
        response = super(UserViewSet, self).list(request, *args, **kwargs)
        if request.accepted_renderer.format != 'json':
            return Response({'users': response.data['results']}, template_name='user-list.html')
        else:
            return JSONResponse({'users': response.data['results']})

    @detail_route(methods=['get'])
    def set_password(self, request, pk=None):
        return Response({'data':'ok'}, template_name='user.html')

    def view_single_case(methods=['get']):
        return Response()

    def create(self, request, *args, **kwargs):
        """
        Create user
        """
        request.data['password'] = request.data.get('password1')
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.create({'email':request.data.get('email'),'password':request.data.get('password')})
                content = {
                'status':'Success!',
                'message':'Thank you. Please check your email %s for a verification link.' % user.email}
                if request.accepted_renderer.format == 'api':
                    return Response(content)
                elif request.accepted_renderer.format == 'json':
                    return JSONResponse(content)
                else:
                    return Response(content, template_name='sign-up-success.html')
            except IntegrityError:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    serializer = LoginSerializer()
    def get(self, request):
        http_method_names=['GET']
        return Response({'data':'login'}, template_name='log-in.html')

@api_view(http_method_names=['GET'])
@parser_classes((FormParser,))
@renderer_classes((renderers.TemplateHTMLRenderer, ))
def sign_up(request):
    """
    Return signup form
    """
    data = {'message':'','email':'', 'password':'', 'first_name':'', 'last_name':''}
    return render(request, 'sign-up.html', {'form': SignupForm})

@api_view(http_method_names=['GET'])
@renderer_classes((renderers.BrowsableAPIRenderer,renderers.JSONRenderer,))
def verify_user(request, user_id, activation_nonce):
    """
    Verify email and assign api token
    """
    serializer = UserSerializer()
    user = serializer.verify_with_nonce(user_id, activation_nonce)
    if user.is_validated:
        api_key = user.get_api_key()
        data = {'email':user.email,'api_key':api_key}
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
        if request.accepted_renderer.format != 'json':
            return Response({'serializer':serializer}, template_name='get-token.html')
        else:
            return JSONResponse(serializer.data)
    elif request.method == 'POST':
        try:
            email = request.data.get('email')
            password = request.data.get('password')
            user = serializer.verify_with_password(email, password)
            if user.is_validated:
                api_key = user.get_api_key()
                data = {'email':user.email,'api_key':api_key}
                if request.accepted_renderer.format != 'json' :
                    return Response(data, template_name='token.html')
                else:
                    return JSONResponse(data)
        except Exception as e:
            data = {'status':'Failed.','message':'Please check that your entered credentials are correct.'}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
