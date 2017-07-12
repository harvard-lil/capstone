import os
from wsgiref.util import FileWrapper
import logging

from django.http import HttpResponse, StreamingHttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import renderers, viewsets, mixins, filters as rs_filters

from . import permissions, resources, serializers, models, filters, settings
from .view_helpers import format_query, make_query, merge_filters

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
    serializer_class = serializers.JurisdictionSerializer
    http_method_names = ['get']
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.JurisdictionFilter
    queryset = models.Jurisdiction.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class VolumeViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.VolumeSerializer
    http_method_names = ['get']
    queryset = models.Volume.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class ReporterViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.ReporterSerializer
    http_method_names = ['get']
    queryset = models.Reporter.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CourtViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.CourtSerializer
    http_method_names = ['get']
    queryset = models.Court.objects.all()
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class CaseViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    """
    Browse all cases
    """
    permission_classes = (permissions.IsCaseUser,)
    serializer_class = serializers.CaseSerializer
    http_method_names = ['get']
    queryset = models.Case.objects.all()
    filter_backends = (rs_filters.SearchFilter, DjangoFilterBackend,)
    search_fields = ('name', 'name_abbreviation', 'court__name', 'reporter__name', 'jurisdiction__name')
    filter_class = filters.CaseFilter
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    lookup_field = 'slug'
    ordering = ('decisiondate',)

    def download_many(self):
        """
        This method handles general downloads.
        See download_one method for specific slug-based downloads.
        """
        cases = self.queryset.all()

        try:
            max_num = int(self.request.query_params.get('max', settings.CASE_DAILY_ALLOWANCE))
        except ValueError:
            # if no max selected, set to daily max
            max_num = settings.CASE_DAILY_ALLOWANCE
            pass

        query_dict = format_query(self.request.query_params, dict())

        # TODO: throttle requests

        queries = list(map(make_query, list(query_dict.items())))
        logger.info("query %s, max_num %s" % (queries, max_num))

        if len(queries) > 0:
            filters = merge_filters(queries, 'AND')
            cases = cases.filter(filters)
            if cases.count() == 0:
                return JSONResponse({'message': 'Request did not return any results.'}, status=404,)

        caseids_list = list(cases.order_by('decisiondate').values_list('caseid', flat=True))[:max_num]
        blacklisted_cases = list(cases.exclude(jurisdiction__name='Illinois').values_list('caseid', flat=True))
        blacklisted_case_count = len(set(caseids_list) & set(blacklisted_cases))

        download_allowed = self.request.user.case_download_allowed(blacklisted_case_count)
        response = self.create_download_response(caseids_list, blacklisted_case_count, allowed=download_allowed)
        return response

    def download_one(self, **kwargs):
        """
        This method handles downloads by specific slug

        :param kwargs: should only consist of slug field right now
         for instance, request might be `/cases/people-v-tower/?type=download`
         kwargs would be {'slug': 'people-v-tower' }
         see serializers.py's CaseSerializer for the `lookup_field` overwrite
         From http://www.django-rest-framework.org/api-guide/generic-views/
         lookup_field - The model field that should be used to for performing object lookup of individual model instances.
         Defaults to 'pk'.

        """
        if not kwargs.get('slug'):
            return JSONResponse({'message': 'Download file error: %s' % e}, status=403,)
        case = models.Case.objects.get(slug=kwargs.get('slug'))

        blacklisted_case_count = 0
        if case.jurisdiction.name != 'Illinois':
            blacklisted_case_count = 1

        download_allowed = self.request.user.case_download_allowed(blacklisted_case_count)
        response = self.create_download_response([case.caseid], blacklisted_case_count, allowed=download_allowed)

        return response

    def create_download_response(self, case_list, blacklisted_case_count, allowed=False):
        if allowed:
            try:
                zip_filename = self.download_cases(case_list, blacklisted_case_count)
                zip_file = "%s/%s" % (settings.CASE_ZIP_DIR, zip_filename)
                response = StreamingHttpResponse(FileWrapper(open(zip_file, 'rb')), content_type='application/zip')
                response['Content-Length'] = os.path.getsize(zip_file)
                response['Content-Disposition'] = 'attachment; filename="%s"' % zip_filename
                return response
            except Exception as e:
                return JSONResponse({'message': 'Download file error: %s' % e}, status=403, )
        else:
            case_allowance = self.request.user.case_allowance
            time_remaining = self.request.user.get_case_allowance_update_time_remaining()
            message = "You have reached your limit of allowed cases. Your limit will reset to default again in %s", time_remaining
            details = """
                      You attempted to download %s cases and your current remaining case limit is %s. 
                      Use the max flag to return a specific number of cases: &max=%s
                      """ % (
                                blacklisted_case_count,
                                case_allowance,
                                case_allowance
                            )

            return JSONResponse({'message': message, 'details': details}, status=403)

    def list(self, *args, **kwargs):
        if not self.request.query_params.get('type') == 'download':
            return super(CaseViewSet, self).list(*args, **kwargs)
        else:
            return self.download_many()

    def retrieve(self, *args, **kwargs):
        if self.request.query_params.get('type') and self.request.query_params.get('type') == 'download':
            return self.download_one(**kwargs)
        else:
            return super(CaseViewSet, self).retrieve(*args, **kwargs)

    def download_cases(self, caseids_list, blacklisted_case_count):
        try:
            if blacklisted_case_count > 0:
                zip_filename = resources.download_blacklisted(self.request.user.id, caseids_list)
                self.request.user.case_allowance -= blacklisted_case_count
                self.request.user.save()
            else:
                zip_filename = resources.download_whitelisted(self.request.user.id, caseids_list)
            return zip_filename
        except Exception as e:
            raise Exception("Download cases error %s" % e)
