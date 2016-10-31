from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import renderers

from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponseRedirect

from rest_framework import routers, viewsets, views, mixins, permissions
from rest_framework.response import Response

from rest_framework.decorators import api_view, detail_route, list_route, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Case
from .view_helpers import *
from .serializers import *
from .permissions import *
from .forms import SignUpForm

class CaseViewSet(viewsets.GenericViewSet,mixins.ListModelMixin):
    http_method_names = ['get']
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    lookup_field='jurisdiction'

    def get_queryset(self):
        query = Q()
        kwargs = self.kwargs
        if len(self.request.query_params.items()):
            kwargs = format_date_queries(self.request.query_params, kwargs)

        if len(kwargs.items()):
            query = map(make_query, kwargs.items())
            query = merge_filters(query, 'AND')

        return self.queryset.filter(query)
    def post(self, request):
        """
        Sign up
        """
        email = request.data.get('email')
        if not email:
            return Response({'data': 'Email address is required'}, status=status.HTTP_404_NOT_FOUND)
        user = self.serializer.create({'email':email,'password':request.data.get('password')})
        return Response({'data':'SUCCESS'}, status=status.HTTP_201_CREATED)

class LoginView(views.APIView):
    serializer = LoginSerializer
    renderer_classes = [renderers.TemplateHTMLRenderer]

@api_view()
def verify_user(request, user_id, activation_nonce):
    serializer = SignupSerializer()
    if request.method == 'GET':
        user = serializer.verify(user_id, activation_nonce)
        if user.is_validated:
            api_key = user.get_api_key()
            data = {'email':user.email,'api_key':api_key}
            if request.accepted_renderer.format == 'html':
                return Response(data, template_name='verified.html')
            else:
                return Response(data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
