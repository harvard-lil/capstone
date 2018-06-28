import urllib
from django.http import HttpResponseRedirect
from django.utils.text import slugify

from rest_framework import viewsets, mixins, renderers
from rest_framework.reverse import reverse

from capdb import models

from capapi import serializers, filters
from capapi import renderers as capapi_renderers


class JurisdictionViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.JurisdictionSerializer
    http_method_names = ['get']
    filter_class = filters.JurisdictionFilter
    queryset = models.Jurisdiction.objects.all()
    lookup_field = 'slug'


class VolumeViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.VolumeSerializer
    http_method_names = ['get']
    queryset = models.VolumeMetadata.objects.all().select_related(
        'reporter'
    ).prefetch_related('reporter__jurisdictions')


class ReporterViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.ReporterSerializer
    http_method_names = ['get']
    filter_class = filters.ReporterFilter
    queryset = models.Reporter.objects.all().prefetch_related('jurisdictions')


class CourtViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.CourtSerializer
    http_method_names = ['get']
    filter_class = filters.CourtFilter
    queryset = models.Court.objects.all().select_related('jurisdiction')
    lookup_field = 'slug'


class CitationViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.CitationWithCaseSerializer
    http_method_names = ['get']
    queryset = models.Citation.objects.all()


class CaseViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,):
    serializer_class = serializers.CaseSerializer
    http_method_names = ['get']
    queryset = models.CaseMetadata.objects.filter(
        duplicative=False,
        jurisdiction__isnull=False,
        court__isnull=False,
    ).select_related(
        'volume',
        'reporter',
        'court'
    ).prefetch_related(
        'citations'
    ).order_by(
        'decision_date', 'id'  # include id to get consistent ordering for cases with same date
    )

    renderer_classes = (
        renderers.JSONRenderer,
        capapi_renderers.BrowsableAPIRenderer,
        capapi_renderers.XMLRenderer,
        capapi_renderers.HTMLRenderer,
    )
    filter_class = filters.CaseFilter
    lookup_field = 'id'

    def is_full_case_request(self):
        return True if self.request.query_params.get('full_case', 'false').lower() == 'true' else False

    def get_queryset(self):
        if self.is_full_case_request():
            return self.queryset.select_related('case_xml')
        else:
            return self.queryset

    def get_serializer_class(self, *args, **kwargs):
        if self.is_full_case_request():
            return serializers.CaseSerializerWithCasebody
        else:
            return self.serializer_class

    def list(self, *args, **kwargs):
        jur_value = self.request.query_params.get('jurisdiction', None)
        jur_slug = slugify(jur_value)

        if not jur_value or jur_slug == jur_value:
            return super(CaseViewSet, self).list(*args, **kwargs)

        query_string = urllib.parse.urlencode(dict(self.request.query_params, jurisdiction=jur_slug), doseq=True)
        new_url = reverse('casemetadata-list') + "?" + query_string
        return HttpResponseRedirect(new_url)

    def retrieve(self, *args, **kwargs):
        # for user's convenience, if user gets /cases/case-citation or /cases/Case Citation
        # we redirect to /cases/?cite=case-citation

        if kwargs.get(self.lookup_field, None):
            slugified = slugify(kwargs[self.lookup_field])
            if '-' in slugified:
                query_string = urllib.parse.urlencode(dict(self.request.query_params, cite=slugified), doseq=True)
                new_url = reverse('casemetadata-list') + "?" + query_string
                return HttpResponseRedirect(new_url)


        return super(CaseViewSet, self).retrieve(*args, **kwargs)


