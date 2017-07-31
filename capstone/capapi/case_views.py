import logging

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import renderers, viewsets, mixins, filters as rs_filters

from . import permissions, resources, serializers, filters
from capdb import models

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
    queryset = models.VolumeMetadata.objects.all()
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
    permission_classes = (permissions.IsAPIUser,)
    serializer_class = serializers.CaseSerializer
    http_method_names = ['get']
    queryset = models.CaseMetadata.objects.all()
    filter_backends = (rs_filters.SearchFilter, DjangoFilterBackend,)
    search_fields = ('name', 'name_abbreviation', 'court__name', 'reporter__name', 'jurisdiction__name')
    filter_class = filters.CaseFilter
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)
    lookup_field = 'case_id'
    ordering = ('decisiondate',)

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
