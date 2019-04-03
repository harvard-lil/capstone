import re
import urllib
from collections import OrderedDict

from django.http import HttpResponseRedirect, FileResponse
from django.utils.text import slugify

from rest_framework import viewsets, renderers, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse

from capapi.middleware import add_cache_header
from capdb import models

from capapi import serializers, filters, permissions, pagination
from capapi import renderers as capapi_renderers
from capdb.models import Citation


class BaseViewSet(viewsets.ReadOnlyModelViewSet):
    http_method_names = ['get']


class JurisdictionViewSet(BaseViewSet):
    serializer_class = serializers.JurisdictionSerializer
    filterset_class = filters.JurisdictionFilter
    queryset = models.Jurisdiction.objects.order_by('name', 'pk')
    lookup_field = 'slug'


class VolumeViewSet(BaseViewSet):
    serializer_class = serializers.VolumeSerializer
    queryset = models.VolumeMetadata.objects.order_by('pk').select_related(
        'reporter'
    ).prefetch_related('reporter__jurisdictions')


class ReporterViewSet(BaseViewSet):
    serializer_class = serializers.ReporterSerializer
    filterset_class = filters.ReporterFilter
    queryset = models.Reporter.objects.order_by('full_name', 'pk').prefetch_related('jurisdictions')


class CourtViewSet(BaseViewSet):
    serializer_class = serializers.CourtSerializer
    filterset_class = filters.CourtFilter
    queryset = models.Court.objects.order_by('name', 'pk').select_related('jurisdiction')
    lookup_field = 'slug'


class CitationViewSet(BaseViewSet):
    serializer_class = serializers.CitationWithCaseSerializer
    queryset = models.Citation.objects.order_by('pk')


class CaseViewSet(BaseViewSet):
    serializer_class = serializers.CaseSerializer
    queryset = models.CaseMetadata.objects.in_scope().select_related(
        'volume',
        'reporter',
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
    filterset_class = filters.CaseFilter
    lookup_field = 'id'

    def is_full_case_request(self):
        return True if self.request.query_params.get('full_case', 'false').lower() == 'true' else False

    def get_queryset(self):
        if self.is_full_case_request():
            return self.queryset.select_related('case_xml', 'body_cache')
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
        # for user's convenience, if user gets /cases/casecitation or /cases/Case Citation (or any non-numeric value)
        # we redirect to /cases/?cite=casecitation
        id = kwargs[self.lookup_field]
        if re.search(r'\D', id):
            normalized_cite = Citation.normalize_cite(id)
            query_string = urllib.parse.urlencode(dict(self.request.query_params, cite=normalized_cite), doseq=True)
            new_url = reverse('casemetadata-list') + "?" + query_string
            return HttpResponseRedirect(new_url)

        return super(CaseViewSet, self).retrieve(*args, **kwargs)


class CaseExportViewSet(BaseViewSet):
    serializer_class = serializers.CaseExportSerializer
    queryset = models.CaseExport.objects.order_by('pk')
    filterset_class = filters.CaseExportFilter

    def list(self, request, *args, **kwargs):
        # mark list requests to filter out superseded downloads by default
        self.request.hide_old_by_default = True
        return super().list(request, *args, **kwargs)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        # filter out superseded downloads for list requests unless with_old=true
        try:
            if self.request.hide_old_by_default and self.request.GET.get('with_old') != 'true':
                queryset = queryset.exclude_old()
        except AttributeError:
            pass

        return queryset

    @action(
        methods=['get'],
        detail=True,
        renderer_classes=(capapi_renderers.PassthroughRenderer,),
        permission_classes=(permissions.CanDownloadCaseExport,),
    )
    def download(self, *args, **kwargs):
        instance = self.get_object()

        # send file
        response = FileResponse(instance.file.open(), content_type='application/zip')
        response['Content-Length'] = instance.file.size
        response['Content-Disposition'] = 'attachment; filename="%s"' % instance.file_name

        # public downloads are cacheable
        if instance.public:
            add_cache_header(response)

        return response


class NgramViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    http_method_names = ['get']
    queryset = models.Ngram.objects.order_by('pk').select_related('w1', 'w2', 'w3')
    filterset_class = filters.NgramFilter
    pagination_class = pagination.SmallCapPagination
    renderer_classes = (
        renderers.JSONRenderer,
        capapi_renderers.NgramBrowsableAPIRenderer,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # cache translation table between jurisdiction slug and ID
        self.jurisdiction_id_to_slug = {v:k for k,v in filters.jurisdiction_slug_to_id.items()}
        self.jurisdiction_id_to_slug[None] = 'total'

    def list(self, request, *args, **kwargs):
        # without specific ngram search, return nothing
        q = self.request.GET.get('q', '').strip()
        if not q:
            return Response({})

        # fetch all unique ngrams for query, and paginate
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        # get counts for each ngram
        out = OrderedDict()
        if page:

            # build lookup table
            ngrams_by_id = {}
            for ngram in page:
                out[str(ngram)] = ngrams_by_id[ngram.pk] = {}

            # fetch all observations, using same query parameters
            observations = models.NgramObservation.objects.filter(ngram__in=page)
            obs_filter = filters.NgramObservationFilter(data=request.query_params, queryset=observations, request=request)
            if not obs_filter.is_valid():
                raise obs_filter.errors
            observations = list(obs_filter.qs.values_list('ngram_id', 'jurisdiction_id', 'year', 'instance_count', 'document_count'))

            # sort with None values first
            observations.sort(key=lambda x: [[y is not None, y] for y in x])

            # organize all observations by ngram, then jurisdiction, then year
            for ngram_id, jurisdiction_id, year, instance_count, document_count in observations:
                jurs = ngrams_by_id[ngram_id]
                jurisdiction_slug = self.jurisdiction_id_to_slug[jurisdiction_id]
                if jurisdiction_slug not in jurs:
                    jurs[jurisdiction_slug] = OrderedDict()
                years = jurs[jurisdiction_slug]
                years[year or "total"] = [instance_count, document_count]

        return self.get_paginated_response(out)
