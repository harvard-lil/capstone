import os
from django.http import HttpResponse, StreamingHttpResponse
from django.db.models import Q
from django.conf import settings
from rest_framework import renderers, viewsets, mixins, filters
from django_filters.rest_framework import DjangoFilterBackend
from wsgiref.util import FileWrapper
from .models import Case, Jurisdiction, Reporter, Court
from .view_helpers import format_query, make_query, merge_filters
from .serializers import *
from .permissions import IsCaseUser
from .filters import *
from .resources import download_blacklisted, download_whitelisted
import logging

logger = logging.getLogger(__name__)

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
    filter_backends = (DjangoFilterBackend,)
    filter_class = JurisdictionFilter
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
    Browse all cases
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
    ordering = ('decisiondate',)

    def download(self, *args, **kwargs):
        cases = self.queryset.all()

        query_dict = {}
        query = Q()

        if len(self.request.query_params.items()):
            query = format_query(self.request.query_params, query_dict)

        try:
            max_num = int(query_dict.pop('max', settings.CASE_DAILY_ALLOWANCE))
        except ValueError:
            max_num = settings.CASE_DAILY_ALLOWANCE
            pass

        # TODO: throttle requests

        queries = map(make_query, query_dict.items())
        logger.info("QUERY IS:", queries)

        if len(queries) > 0:
            filters = merge_filters(queries, 'AND')
            cases = cases.filter(filters)

        if not len(cases):
            return JSONResponse({'message': 'Request did not return any results.'}, status=404,)

        caseids_list = list(cases.order_by('decisiondate').values_list('caseid', flat=True))[:max_num]
        blacklisted_cases = list(cases.exclude(jurisdiction__name='Illinois').values_list('caseid', flat=True))
        blacklisted_case_count = len(set(caseids_list) & set(blacklisted_cases))

        if blacklisted_case_count > 0:
            try:
                has_case_permissions = self.check_case_permissions(blacklisted_case_count)
            except:
                return JSONResponse({'message': 'Error reading user permissions'}, status=403,)
        else:
            has_case_permissions = True

        if has_case_permissions:
            try:
                zip_filename = self.download_cases(caseids_list, blacklisted_case_count)
                zip_file = "%s/%s" % (settings.CASE_ZIP_DIR, zip_filename)
                response = StreamingHttpResponse(FileWrapper(open(zip_file, 'rb')), content_type='application/zip')
                response['Content-Length'] = os.path.getsize(zip_file)
                response['Content-Disposition'] = 'attachment; filename="%s"' % zip_filename
                return response
            except Exception as e:
                return JSONResponse({'message': 'Download file error: %s' % e}, status=403,)
        else:
            case_allowance = self.request.user.case_allowance
            time_remaining = self.request.user.get_case_allowance_update_time_remaining()
            message = "You have reached your limit of allowed cases. Your limit will reset to default again in %s", time_remaining
            details = "You attempted to download %s cases and your current remaining case limit is %s. Use the max flag to return a specific number of cases: &max=%s" % (blacklisted_case_count, case_allowance, case_allowance)
            return JSONResponse({'message': message, 'details': details}, status=403)

    def check_case_permissions(self, case_count):
        self.request.user.update_case_allowance()
        return self.request.user.case_allowance >= case_count

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

    def download_cases(self, caseids_list, blacklisted_case_count):
        try:
            if blacklisted_case_count > 0:
                zip_filename = download_blacklisted(self.request.user.id, caseids_list)
                self.request.user.case_allowance -= blacklisted_case_count
                self.request.user.save()
            else:
                zip_filename = download_whitelisted(self.request.user.id, caseids_list)
            return zip_filename
        except Exception as e:
            raise Exception("Download cases error %s" % e)
