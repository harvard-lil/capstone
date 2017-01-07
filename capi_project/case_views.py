import os
from django.shortcuts import get_object_or_404
from rest_framework import renderers, status
from django.http import HttpResponse, StreamingHttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Q
from rest_framework import routers, viewsets, views, mixins, permissions
from rest_framework.response import Response

from rest_framework.decorators import api_view, detail_route, list_route, permission_classes, renderer_classes, parser_classes
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from wsgiref.util import FileWrapper

from .models import Case, Jurisdiction, Reporter, Court
from .view_helpers import *
from .serializers import *
from .permissions import IsCaseUser
from .filters import *

from resources import scp_get

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = renderers.JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

class JurisdictionViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = JurisdictionSerializer
    http_method_names = ['get']
    queryset = Jurisdiction.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)

class VolumeViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = VolumeSerializer
    http_method_names = ['get']
    queryset = Volume.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)

class ReporterViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = ReporterSerializer
    http_method_names = ['get']
    queryset = Reporter.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)

class CourtViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = CourtSerializer
    http_method_names = ['get']
    queryset = Court.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)

class CaseViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    """
    # Browse all cases
    """
    permission_classes = (IsCaseUser,)
    serializer_class = CaseSerializer
    http_method_names = ['get']
    queryset = Case.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_class = CaseFilter
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    lookup_field = 'slug'
    #
    # def case_list(self, *args, **kwargs):
    #     query = Q()
    #     kwargs = self.kwargs
    #
    #     cases = self.queryset.all()
    #
    #     if len(self.request.query_params.items()):
    #         kwargs = format_kwargs(self.request.query_params, kwargs)
    #
    #     max_num = kwargs.pop('max', None)
    #     fields = kwargs.pop('fields', None)
    #     offset = kwargs.pop('offset', 0)
    #     response_format = kwargs.pop('format', None)
    #
    #     if fields:
    #         fields = fields.split(',')
    #         # caseid is required
    #         if 'caseid' not in fields:
    #             fields.append('caseid')
    #
    #
    #     if len(kwargs.items()):
    #         query = map(make_query, kwargs.items())
    #         query = merge_filters(query, 'AND')
    #
    #         cases = cases.filter(query)
    #
    #     if fields:
    #         cases = cases.values(*fields)
    #
    #     if not kwargs.get('type') == 'download':
    #         cases = list(cases.order_by('caseid'))
    #         page = self.paginate_queryset(cases)
    #         serializer = self.get_serializer(cases, many=True)
    #
    #         return self.get_paginated_response(serializer.data)
    #     else:
    #         has_permissions = self.check_case_permissions(cases)
    #         if has_permissions:
    #             try:
    #                 zip_file_name = self.download_cases(cases)
    #                 response = StreamingHttpResponse(FileWrapper(open(zip_file_name, 'rb')), content_type='application/zip')
    #                 response['Content-Length'] = os.path.getsize(zip_file_name)
    #                 response['Content-Disposition'] = 'attachment; filename="%s"' % zip_file_name
    #                 return response
    #             except Exception as e:
    #                 Exception("Download file error: %s" % e)
    #         else:
    #             raise Exception("You have reached your limit of allowed cases")
    #
    # def check_case_permissions(self, cases):
    #     self.request.user.update_case_allowance()
    #     user = CaseUser.objects.get(email=self.request.user.email)
    #     return user.case_allowance >= len(cases)
    #
    # def download_cases(self, cases):
    #     case_ids = cases.values_list('caseid', flat=True)
    #     try:
    #         cases = scp_get(self.request.user.id, case_ids)
    #         self.request.user.case_allowance -= len(case_ids)
    #         self.request.user.save()
    #         return cases
    #     except Exception as e:
    #         raise Exception("Download cases error %s" % e)
