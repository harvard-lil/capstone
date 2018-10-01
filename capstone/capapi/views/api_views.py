import re
import urllib

from django.db.models import Sum
from django.http import HttpResponseRedirect, FileResponse
from django.utils.text import slugify

from rest_framework import viewsets, renderers
from rest_framework.decorators import action
from rest_framework.reverse import reverse

from capapi.middleware import add_cache_header
from capdb import models

from capapi import serializers, filters, permissions
from capapi import renderers as capapi_renderers
from capdb.models import Citation
from scripts.ngrams import tokenize


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
    queryset = models.CaseMetadata.objects.filter(
        duplicative=False,
        jurisdiction__isnull=False,
        court__isnull=False,
    ).select_related(
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


class NgramViewSet(BaseViewSet):
    serializer_class = serializers.NgramSerializer
    queryset = models.Ngram.objects.order_by('year')
    filterset_class = filters.NgramFilter

    def filter_queryset(self, queryset):
        """ Handle q= query parameter. """
        queryset = super().filter_queryset(queryset)

        q = self.request.GET.get('q', '').strip()
        if q:
            # get first three tokens from q
            words = list(tokenize(q.strip()))[:3]

            # find IDs of those tokens in DB
            word_objs = list(models.NgramWord.objects.filter(word__in=words))

            if len(word_objs) < len(words):
                # if all three tokens aren't in DB, no match
                queryset = queryset.none()
            else:
                # Get the ngram counts for each year.
                # This is basically the ORM equivalent of the following SQL
                # (plus automatic handling of NULLs and jurisdiction filtering):
                #   SELECT SUM(count) FROM capdb_ngram WHERE w1=words[1] AND w2=words[2] AND w3=words[3] GROUP BY year;
                words_dict = {w.word: w for w in word_objs}
                word_ids = [words_dict[w] for w in words]
                keys = ['w1', 'w2', 'w3'][:len(words)]
                queryset = queryset.filter(**dict(zip(keys, word_ids)))
                queryset = queryset.values(*(keys+['year'])).annotate(count=Sum('count'))
        else:
            # without a query, return nothing
            queryset = queryset.none()

        return queryset

