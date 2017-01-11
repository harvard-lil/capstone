import os
from django.shortcuts import get_object_or_404
from rest_framework import renderers, status
from django.http import HttpResponse, StreamingHttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Q
from rest_framework import routers, viewsets, views, mixins, permissions, filters
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
    filter_backends = (filters.SearchFilter, DjangoFilterBackend,)
    search_fields = ('name', 'name_abbreviation', 'court__name', 'reporter__name', 'jurisdiction__name')
    filter_class = CaseFilter
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    lookup_field = 'slug'
    ordering = ('decisiondate')

    def download(self, *args, **kwargs):
        query = Q()
        kwargs = self.kwargs
        cases = self.queryset.all()
        if len(self.request.query_params.items()):
            kwargs = format_kwargs(self.request.query_params, kwargs)

        max_num = kwargs.pop('max', None)
        kwargs.pop('type')

        min_year = kwargs.pop('min_year', None)
        max_year = kwargs.pop('max_year', None)

        kwargs['reporter__name'] = kwargs.pop('reporter', '')
        kwargs['jurisdiction__name'] = kwargs.pop('jurisdiction', '')
        kwargs['court__name'] = kwargs.pop('court', '')

        if len(kwargs.items()):
            query = map(make_query, kwargs.items())
            query = merge_filters(query, 'AND')

            cases = cases.filter(query)

        if max_num:
            max_num = int(max_num)
            cases = cases[:max_num]

        try:
            has_permissions = self.check_case_permissions(cases)
        except:
            return Response({'message': 'Error reading user permissions'}, status=403,)
            
        if has_permissions:
            try:
                zip_file_name = self.download_cases(cases)
                response = StreamingHttpResponse(FileWrapper(open(zip_file_name, 'rb')), content_type='application/zip')
                response['Content-Length'] = os.path.getsize(zip_file_name)
                response['Content-Disposition'] = 'attachment; filename="%s"' % zip_file_name
                return response
            except Exception as e:
                return Response({'message': 'Download file error: %s' % e}, status=403,)
        else:
            requested_case_amount = len(cases)
            case_allowance = self.request.user.case_allowance
            time_remaining = self.request.user.get_case_allowance_update_time_remaining()
            message = 'You have reached your limit of allowed cases. Your limit will reset to default again in %s', time_remaining
            details = "You attempted to download %s cases and your current remaining case limit is %s. Use the max flag to return a specific number of cases: &max=%s" % (requested_case_amount, case_allowance, case_allowance)
            return Response({'message':message, 'details':details}, status=403)

    def check_case_permissions(self, cases):
        self.request.user.update_case_allowance()
        user = CaseUser.objects.get(email=self.request.user.email)
        return user.case_allowance >= len(cases)

    def list(self, *args, **kwargs):
        if not self.request.query_params.get('type') == 'download':
            return super(CaseViewSet, self).list(*args, **kwargs)
        else:
            return self.download(args, kwargs)

    def retrieve(self, *args, **kwargs):
        if not self.request.query_params.get('type') == 'download':
            return super(CaseViewSet, self).retrieve(*args, **kwargs)
        else:
            return self.download(args, kwargs)

    def download_cases(self, cases):
        case_ids = cases.values_list('caseid', flat=True)
        try:
            cases = scp_get(self.request.user.id, case_ids)
            self.request.user.case_allowance -= len(case_ids)
            self.request.user.save()
            return cases
        except Exception as e:
            raise Exception("Download cases error %s" % e)
