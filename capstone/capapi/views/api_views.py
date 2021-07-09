import bisect
import urllib
from datetime import datetime, date
from collections import OrderedDict, defaultdict
from pathlib import Path

from django.utils.functional import partition
from rest_framework import viewsets, renderers, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django_elasticsearch_dsl_drf.filter_backends import DefaultOrderingFilterBackend, HighlightBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet as DEDDBaseDocumentViewSet
from django.http import QueryDict, HttpRequest, HttpResponseRedirect, FileResponse, HttpResponseBadRequest, StreamingHttpResponse

from capapi import serializers, filters, permissions, renderers as capapi_renderers
from capapi.documents import CaseDocument, RawSearch, ResolveDocument
from capapi.pagination import CapESCursorPagination
from capapi.resources import api_request
from capapi.serializers import CaseDocumentSerializer, ResolveDocumentSerializer
from capapi.middleware import add_cache_header
from capdb import models
from capdb.models import CaseMetadata
from capdb.storages import ngram_kv_store_ro
from scripts.helpers import normalize_cite
from user_data.models import UserHistory


class BaseDocumentViewSet(DEDDBaseDocumentViewSet):
    pagination_class = CapESCursorPagination

    def __init__(self, *args, **kwargs):
        # use RawSearch to avoid using Elasticsearch wrappers, for speed
        super().__init__(*args, **kwargs)
        self.search.__class__ = RawSearch

    # this lets DRF handle 'not found' issues the way they they are with the DB back end
    ignore = [404]

    lookup_field = 'id'

    simple_query_string_options = {
        "default_operator": "and",
    }

    filterset_fields = []  # make CaseFilter, which we use just for presentation in the HTML viewer, ignore filter_fields, which we use for filtering on Elasticsearch

    # Specify default ordering. Relevance is a synonym for score, so we reverse it. It's reversed in the user-specified
    # ordering backend.
    ordering = ('-relevance', 'decision_date')

    def filter_queryset(self, queryset):
        queryset = super(BaseDocumentViewSet, self).filter_queryset(queryset)
        return queryset.extra(track_total_hits=True)


class BaseViewSet(viewsets.ReadOnlyModelViewSet):
    http_method_names = ['get']


class JurisdictionViewSet(BaseViewSet):
    serializer_class = serializers.JurisdictionSerializer
    filterset_class = filters.JurisdictionFilter
    queryset = models.Jurisdiction.objects.order_by('name', 'pk')
    lookup_field = 'slug'


class VolumeViewSet(BaseViewSet):
    serializer_class = serializers.VolumeSerializer
    filterset_class = filters.VolumeFilter
    queryset = models.VolumeMetadata.objects.filter(out_of_scope=False).order_by('pk').select_related(
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


class CaseDocumentViewSet(BaseDocumentViewSet):
    """The CaseDocument view."""
    document = CaseDocument
    serializer_class = CaseDocumentSerializer
    filterset_class = filters.CaseFilter

    filter_backends = [
        # queries that take full-text search operators:
        filters.MultiFieldFTSFilter,
        filters.NameFTSFilter,
        filters.NameAbbreviationFTSFilter,
        filters.DocketNumberFTSFilter,
        filters.CaseFilterBackend, # Facilitates Filtering (Filters)
        filters.CAPOrderingFilterBackend, # Orders Document
        HighlightBackend, # for search preview
        DefaultOrderingFilterBackend # Must be last
    ]

    # Define filter fields
    filter_fields = {
        'id': 'id',
        'court': 'court.slug',
        'court_id': 'court.id',
        'reporter': 'reporter.id',
        'jurisdiction': 'jurisdiction.slug',
        'cite': 'citations.normalized_cite',
        'cites_to': 'extracted_citations.normalized_cite',
        'cites_to_id': 'extracted_citations.target_cases',
        'cites_to.reporter': 'extracted_citations.reporter',
        'cites_to.category': 'extracted_citations.category',
        'decision_date': 'decision_date_original',
        'last_updated': 'last_updated',
        **{'analysis.'+k: 'analysis.'+k for k in filters.analysis_fields},
        # legacy fields:
        'decision_date_min': {'field': 'decision_date_original', 'default_lookup': 'gte'},
        'decision_date_max': {'field': 'decision_date_original', 'default_lookup': 'lte'},
    }

    # Define ordering fields
    ordering_fields = {
        'relevance': '_score',
        'decision_date': 'decision_date_original',
        'name_abbreviation': 'name_abbreviation.raw',
        'id': 'id',
        'last_updated': 'last_updated',
        **{'analysis.' + k: 'analysis.' + k for k in filters.analysis_fields},
    }

    highlight_fields = {
        'casebody_data.text.head_matter': {
            'options': {
                'pre_tags': ["<em class='search_highlight'>"],
                'post_tags': ["</em>"]
            },
            'enabled': True,
        },
        'casebody_data.text.opinions.author': {
            'options': {
                'pre_tags': ["<em class='search_highlight'>"],
                'post_tags': ["</em>"]
            },
            'enabled': True,
        },
        'casebody_data.text.opinions.text': {
            'options': {
                'pre_tags': ["<em class='search_highlight'>"],
                'post_tags': ["</em>"]
            },
            'enabled': True,
        },
        'casebody_data.text.corrections': {
            'options': {
                'pre_tags': ["<em class='search_highlight'>"],
                'post_tags': ["</em>"]
            },
            'enabled': True,
        },
    }

    def is_full_case_request(self):
        return True if self.request.query_params.get('full_case', 'false').lower() == 'true' else False

    def get_serializer_class(self, *args, **kwargs):
        if self.is_full_case_request():
            return serializers.CaseDocumentSerializerWithCasebody
        else:
            return self.serializer_class

    def filter_queryset(self, queryset):
        queryset = super(CaseDocumentViewSet, self).filter_queryset(queryset)
        # exclude all values from casebody_data that we don't need to complete the request
        if self.is_full_case_request():
            data_formats_to_exclude = ["text", "html", "xml"]

            try:
                data_formats_to_exclude.remove(self.request.query_params.get('body_format', 'text'))
            except ValueError:
                # defaults to sending text if it's a full case request with no body_format specified.
                data_formats_to_exclude.remove('text')

            source_filter = {"excludes": ["casebody_data.%s" % format for format in data_formats_to_exclude]}
        else:
            source_filter = {"excludes": "casebody_data.*"}

        return queryset.source(source_filter)

    def get_renderers(self):
        if self.action == 'retrieve':
            return [renderers.JSONRenderer(), capapi_renderers.PdfRenderer(), capapi_renderers.BrowsableAPIRenderer(), capapi_renderers.CSVRenderer()]
        else:
            return [renderers.JSONRenderer(), capapi_renderers.BrowsableAPIRenderer(), capapi_renderers.CSVRenderer()]

    def retrieve(self, request, *args, **kwargs):
        # for user's convenience, if user gets /cases/casecitation or /cases/Case Citation (or any non-numeric value)
        # we redirect to /cases/?cite=casecitation
        id = kwargs[self.lookup_field]
        if not id.isdigit():
            normalized_cite = normalize_cite(id)
            query_string = urllib.parse.urlencode(dict(self.request.query_params, cite=normalized_cite), doseq=True)
            new_url = reverse('cases-list') + "?" + query_string
            return HttpResponseRedirect(new_url)

        if self.request.query_params.get('format') == 'html':
            # if previously-supported format=html is requested, redirect to frontend_url
            case = models.CaseMetadata.objects.filter(id=id).first()
            if case:
                return HttpResponseRedirect(case.get_full_frontend_url())

        # handle ?format=pdf
        if request.accepted_renderer.format == 'pdf':
            data = self.get_serializer(self.get_object()).data
            if 'casebody' not in data:
                return HttpResponseBadRequest("full_case=true is required for format=pdf")
            if data['casebody']['status'] != 'ok':
                return HttpResponseBadRequest(data['casebody']['status'])
            case = CaseMetadata.objects.get(pk=data['id'])
            if not case.pdf_available():
                return HttpResponseBadRequest("pdf is not available for this case")
            return Response(case.get_pdf())

        response = super(CaseDocumentViewSet, self).retrieve(request, *args, **kwargs)

        # handle ?format=csv
        if request.accepted_renderer.format == 'csv':
            response = self.bundle_csv_response(response)

        return response

    def list(self, request, *args, **kwargs):
        # cites_to can contain citations or IDs, so split out IDs into separate
        # cites_to_id parameter
        if 'cites_to' in request.query_params:
            request._request.GET = params = request._request.GET.copy()
            cites_to, cites_to_id = partition(lambda c: c.isdigit(), params.getlist('cites_to'))
            params.setlist('cites_to', cites_to)
            params.setlist('cites_to_id', cites_to_id)

        response = super(CaseDocumentViewSet, self).list(request, *args, **kwargs)

        if request.accepted_renderer.format == 'csv':
            response = self.bundle_csv_response(response)

        if request.accepted_renderer.format == 'json': #shouldn't affect the browsable API
            response['Content-Disposition'] = 'attachment; filename="CAP_{}.json"'.format(str(datetime.now()))

        return response

    @staticmethod
    def bundle_csv_response(response):
        data = capapi_renderers.CSVRenderer().render(response.data)
        response = StreamingHttpResponse(data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="CAP_{}.csv"'.format(str(datetime.now()))
        return response

class ResolveDocumentViewSet(BaseDocumentViewSet):
    """The ResolveDocument view."""

    document = ResolveDocument
    serializer_class = ResolveDocumentSerializer
    filterset_class = filters.ResolveFilter
    pagination_class = None

    filter_backends = [
        filters.ResolveFilterBackend,
    ]

    # Define filter fields
    filter_fields = {
        'q': 'citations.normalized_cite',
    }

    retrieve = None

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


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
    filterset_class = filters.NgramFilter
    queryset = models.CaseMetadata.objects.all()  # fake queryset just to get the filterset to render in the API viewer
    renderer_classes = (
        renderers.JSONRenderer,
        capapi_renderers.NgramBrowsableAPIRenderer,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # cache translation table between jurisdiction slug and ID

        self.jurisdiction_id_to_slug = dict(models.Jurisdiction.objects.values_list('pk', 'slug'))
        self.jurisdiction_id_to_slug[None] = 'total'
        self.jurisdiction_slug_to_id = {v:k for k,v in self.jurisdiction_id_to_slug.items()}
        self.totals_by_jurisdiction_year_length = self.load_totals()

    @staticmethod
    def load_totals():
        # populate self.totals_by_jurisdiction_year_length, a mapping of jurisdiction-year-length to counts, like:
        #   {
        #       (<jur_id>, <year>, <length>): (<word count>, <document count>),
        #   }
        if not Path(ngram_kv_store_ro.db_path()).exists():
            return {}
        totals_by_jurisdiction_year_length = defaultdict(lambda: [0,0])
        for k, v in ngram_kv_store_ro.get_prefix(b'totals', packed=True):
            jur, year, n = ngram_kv_store_ro.unpack(k[len(b'totals'):])
            totals_by_jurisdiction_year_length[(jur, year, n)] = v
            for total in (
                totals_by_jurisdiction_year_length[(None, year, n)],
                totals_by_jurisdiction_year_length[(None, None, n)]
            ):
                total[0] += v[0]
                total[1] += v[1]
        return totals_by_jurisdiction_year_length

    @staticmethod
    def get_valid_case_id(q):
        # validate whether a case ID exists in the corpus
        noresult = (False, False)
        # check if the supplied item is a valid case id
        if not q or not q.endswith('@'):
            return noresult

        caseid = q[:-1]

        if not caseid.isdigit():
            return noresult

        # check if the case id is valid
        case = models.CaseMetadata.objects.filter(id=int(caseid)).first()

        if case:
            year = case.decision_date.year

        return (year, caseid) if case else noresult

    @staticmethod
    def clone_request(request, method, renderer, query_params):
        # copy a request object with specified query changes
        new_request = HttpRequest()
        new_request.method = method
        new_request.accepted_renderer = renderer
        new_request.META = request.META
        new_request.query_params = query_params
        new_request.GET = QueryDict(mutable=True)
        new_request.GET.update(query_params)

        return new_request

    def get_best_jurisdictions(self, request, case_id):
        # TODO: Efficiently support wildcard jurisdictions for case citations
        pass

    def get_citation_data(self, request, case_id, decisionyear):
        # given a case and its decision year, generate the timelien for the trends API.
        currentyear = date.today().year

        results = OrderedDict()
        out = {}
        # ready handler for extracting case counts
        casescaller = CaseDocumentViewSet.as_view({'get': 'list'})

        # hold onto jurisdiction to tag field name later
        jurisdiction = request.GET.getlist('jurisdiction')

        years_out = []
        for year in range(decisionyear, currentyear):
            # get count for every single year from publication up to current year
            request_params = {'cites_to_id': case_id, 'page_size': '1', 'decision_date__gte': str(year), 'decision_date__lt': str(year+1)}
            request_params_total = {'page_size': '1', 'decision_date__gte': str(year), 'decision_date__lt': str(year+1)}

            # filter for jurisdictions
            if jurisdiction:
                if '*' not in jurisdiction[0]:
                    request_params['jurisdiction'] = jurisdiction[0]

            api_request = self.clone_request(request, 'GET', 'json', request_params)
            api_request_total = self.clone_request(request, 'GET', 'json', request_params_total)

            cited_to_cases = casescaller(api_request, {}).data
            cite_count = cited_to_cases.popitem(last=False)

            cited_to_cases_total = casescaller(api_request_total, {}).data
            count_total = cited_to_cases_total.popitem(last=False)

            if cite_count[0] != 'count' or count_total[0] != 'count':
                raise Exception('Schema change for case listing prevents ngrams from retrieving case count')

            if cite_count[1] == 0:
                continue

            years_out.append(OrderedDict((
                ("year", str(year)),
                ("count", [cite_count[1], count_total[1]]),
                ("doc_count", [cite_count[1], count_total[1]])
            )))

        juris_key = jurisdiction[0] if jurisdiction else 'total'
        out[juris_key] = years_out
        results[case_id + ", citations"] = out

        return results

    def list(self, request, *args, **kwargs):
        # without specific ngram search, return nothing
        q = self.request.GET.get('q', '').strip().lower()
        if not q:
            return Response({})

        ## look up query in KV store
        words = q.split(' ')[:3]  # use first 3 words

        # check if we're querying for a case as opposed to a word
        decisionyear, case_id = self.get_valid_case_id(q)

        q_len = len(words)
        # prepend word count as first byte
        q = bytes([q_len]) + ' '.join(words).encode('utf8')

        if case_id:
            results = self.get_citation_data(request, case_id, decisionyear)
            pairs = []
        elif q.endswith(b' *'):
            results = OrderedDict()      
            # wildcard search
            pairs = ngram_kv_store_ro.get_prefix(q[:-1], packed=True)
        else:
            results = OrderedDict()      
            # non-wildcard search
            value = ngram_kv_store_ro.get(q, packed=True)
            if value:
                pairs = [(q, value)]
            else:
                pairs = []

        ## format results
        if pairs:
            # prepare jurisdiction_filter from jurisdiction= query param
            jurisdictions = request.GET.getlist('jurisdiction')
            if '*' in jurisdictions:
                jurisdiction_filter = None
            else:
                jurisdiction_filter = set(self.jurisdiction_slug_to_id[j] for j in jurisdictions if j in self.jurisdiction_slug_to_id)
                if not jurisdiction_filter:
                    jurisdiction_filter.add(None)

            # prepare year_filter from year= query param
            year_filter = set()
            for year in request.GET.getlist('year'):
                if year.isdigit():
                    year_filter.add(int(year))

            # get top 10 pairs
            top_pairs = []
            for gram, data in pairs:
                total_jur = data[None]
                sort_count = total_jur[None][0]
                bisect.insort_right(top_pairs, (sort_count, gram, data))
                top_pairs = top_pairs[-10:]

            # Reformat stored gram data for delivery.
            # top_pairs will look like:
            #   [
            #     (<sort_count>, b'<wordcount><gram>', {
            #       <jur_id>: [
            #         <year - 1900>, <instance_count>, <document_count>,
            #         <year - 1900>, <instance_count>, <document_count>, ...
            #     ]),
            #  ]
            # this reformats to:
            #  {
            #    <jurisdiction slug>: [
            #      {
            #        'year': <year>,
            #        'count': [<instance_count>, <total instances>],
            #        'doc_count': [<instance_count>, <total instances>],
            #      }
            #    ]
            #  }
            for _, gram, data in reversed(top_pairs):
                out = {}
                for jur_id, years in data.items():

                    # apply jurisdiction_filter
                    if jurisdiction_filter and jur_id not in jurisdiction_filter:
                        continue

                    years_out = []
                    jur_slug = self.jurisdiction_id_to_slug[jur_id]
                    if jur_id is None:
                        years = [i for k, v in years.items() for i in [k]+v]
                    for i in range(0, len(years), 3):
                        year, count, doc_count = years[i:i+3]

                        # filter out total
                        if year is None:
                            continue

                        # years will be -1900 for msgpack compression -- add 1900 back in
                        year += 1900

                        # apply year filter
                        if year_filter and year not in year_filter:
                            continue

                        totals = self.totals_by_jurisdiction_year_length[(jur_id, year, q_len)]
                        years_out.append(OrderedDict((
                            ("year", str(year) if year else "total"),
                            ("count", [count, totals[0]]),
                            ("doc_count", [doc_count, totals[1]]),
                        )))

                    years_out.sort(key=lambda y: y["year"])
                    out[jur_slug] = years_out

                if out:
                    results[gram[1:].decode('utf8')] = out

        paginated = OrderedDict((
            ("count", len(results)),
            ("next", None),
            ("previous", None),
            ("results", results),
        ))

        return Response(paginated)


class UserHistoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    http_method_names = ['get']
    queryset = UserHistory.objects.all()
    filterset_class = filters.UserHistoryFilter
    serializer_class = serializers.UserHistorySerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return self.queryset.none()
        return self.queryset.filter(user_id=user.id)
