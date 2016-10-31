from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import renderers
from django.http import HttpResponse

from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponseRedirect

from rest_framework import routers, viewsets, views, mixins, permissions
from rest_framework.response import Response

from rest_framework.decorators import api_view, detail_route, list_route, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated

from .models import Case
from .view_helpers import *
from .serializers import *
from .permissions import *
from .forms import SignUpForm


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = renderers.JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

class CaseViewSet(viewsets.GenericViewSet,mixins.ListModelMixin):
    http_method_names = ['get']
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    lookup_field='jurisdiction'
    renferer_classes = (renderers.JSONRenderer, renderers.TemplateHTMLRenderer)
    def get_queryset(self):
        query = Q()
        kwargs = self.kwargs
        if len(self.request.query_params.items()):
            kwargs = format_date_queries(self.request.query_params, kwargs)

        if len(kwargs.items()):
            query = map(make_query, kwargs.items())
            query = merge_filters(query, 'AND')

        return self.queryset.filter(query)

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    renderer_classes = (renderers.JSONRenderer, renderers.TemplateHTMLRenderer)
    queryset = CaseUser.objects.all()
    def list(self, request, *args, **kwargs):
        response = super(UserViewSet, self).list(request, *args, **kwargs)
        if request.accepted_renderer.format == 'html':
            return Response({'users': response.data['results']}, template_name='user-list.html')
        else:
            return JSONResponse({'users': response.data['results']})

    @detail_route(methods=['get'])
    def set_password(self, request, pk=None):
        return Response({'data':'ok'}, template_name='user.html')

    def create(self, request, *args, **kwargs):
        """
        Create user
        """
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.create({'email':request.data.get('email'),'password':request.data.get('password')})
            if request.accepted_renderer.format != 'json':
                return Response({'user':user}, status=status.HTTP_201_CREATED, template_name='sign-up-success.html')
            else:
                return JSONResponse({'data':'SUCCESS'}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    serializer = LoginSerializer()
    def get(self, request):
        http_method_names=['GET']

        return Response({'data':'login'}, template_name='log-in.html')

@renderer_classes(renderers.TemplateHTMLRenderer)
@api_view(http_method_names=['GET'])
def sign_up(request):
    """
    Return signup form
    """

    serializer = UserSerializer()
    return Response({'user':serializer.instance, 'serializer':serializer}, template_name='sign-up.html')

@api_view()
def verify_user(request, user_id, activation_nonce):
    serializer = UserSerializer()
    if request.method == 'GET':
        user = serializer.verify(user_id, activation_nonce)
        if user.is_validated:
            api_key = user.get_api_key()
            data = {'email':user.email,'api_key':api_key}
            if request.accepted_renderer.format == 'html' or request.accepted_renderer.format == 'api':
                return Response(data, template_name='verified.html')
            else:
                return JSONResponse(data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
