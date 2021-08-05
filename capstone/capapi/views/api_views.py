import bisect
import urllib
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

from django.utils.functional import partition
from rest_framework import viewsets, renderers, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django_elasticsearch_dsl_drf.filter_backends import DefaultOrderingFilterBackend, HighlightBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet as DEDDBaseDocumentViewSet
from django.http import QueryDict, HttpResponseRedirect, FileResponse, HttpResponseBadRequest
from elasticsearch_dsl import TermsFacet, DateHistogramFacet
from rest_framework.exceptions import ValidationError

from capapi import serializers, filters, permissions, renderers as capapi_renderers
from capapi.documents import CaseDocument, RawSearch, ResolveDocument
from capapi.pagination import CapESCursorPagination
from capapi.serializers import CaseDocumentSerializer, ResolveDocumentSerializer
from capapi.middleware import add_cache_header
from capapi.resources import api_request
from capdb import models
from capdb.models import CaseMetadata
from capdb.storages import ngram_kv_store_ro
from capweb.helpers import cache_func
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

    query_filter_backends = [
        # queries that take full-text search operators:
        filters.MultiFieldFTSFilter,
        filters.NameFTSFilter,
        filters.AuthorFTSFilter,
        filters.AuthorTypeFTSFilter,
        filters.NameAbbreviationFTSFilter,
        filters.MultiNestedFilteringFilterBackend,
        filters.DocketNumberFTSFilter,
        filters.CitesToDynamicFilter,
        filters.CaseFilterBackend, # Facilitates Filtering (Filters)
    ]
    result_filter_backends = [
        filters.CAPOrderingFilterBackend, # Orders Document
        filters.CAPFacetedSearchFilterBackend, # Aggregates Document
        HighlightBackend, # for search preview
        DefaultOrderingFilterBackend # Must be last
    ]
    filter_backends = query_filter_backends + result_filter_backends

    # Define filter fields
    filter_fields = {
        'id': 'id',
        'court': 'court.slug',
        'court_id': 'court.id',
        'reporter': 'reporter.id',
        'jurisdiction': 'jurisdiction.slug',
        'cite': 'citations.normalized_cite',
        'decision_date': 'decision_date_original',
        'last_updated': 'last_updated',

        **{'analysis.'+k: 'analysis.'+k for k in filters.analysis_fields},
        # legacy fields:
        'decision_date_min': {'field': 'decision_date_original', 'default_lookup': 'gte'},
        'decision_date_max': {'field': 'decision_date_original', 'default_lookup': 'lte'},
    }

    faceted_search_fields = { 
        'jurisdiction': {
            'field': 'jurisdiction.slug',
            'facet': TermsFacet,
            'options': {
                'size': 200,
            }
        },
        'decision_date': {
            'field': 'decision_date',
            'facet': DateHistogramFacet,
            'options': {
                'interval': 'year',
            },
        },
    }

    faceted_search_param = 'facet'

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
        'casebody_data.text.corrections': {
            'options': {
                'pre_tags': ["<em class='search_highlight'>"],
                'post_tags': ["</em>"]
            },
            'enabled': True,
        },
    }

    highlight_nested_fields = {
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
    }

    search_nested_fields = {
        'author_type': {
            'path': 'casebody_data.text.opinions',
            'fields': ['author', 'type', 'text'],
        }
    }

    nested_filter_fields = {
        'cites_to': {
            'field': 'casebody_data.text.opinions.extracted_citations.normalized_cite',
            'path': ['casebody_data.text.opinions','casebody_data.text.opinions.extracted_citations'],
        },
        'cites_to_id': {
            'field': 'casebody_data.text.opinions.extracted_citations.target_cases',
            'path': ['casebody_data.text.opinions','casebody_data.text.opinions.extracted_citations'],
        },   
        'cites_to.reporter': {
            'field': 'casebody_data.text.opinions.extracted_citations.reporter',
            'path': ['casebody_data.text.opinions','casebody_data.text.opinions.extracted_citations'],
        },  
        'cites_to.category': {
            'field': 'casebody_data.text.opinions.extracted_citations.category',
            'path': ['casebody_data.text.opinions','casebody_data.text.opinions.extracted_citations'],
        }      
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.valid_query_fields = [
            *[field.name for backend in self.query_filter_backends 
                for field in backend().get_schema_fields(self)],
            *[backend.search_param for backend in self.query_filter_backends 
                if hasattr(backend, 'search_param')]
        ]

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
        data_formats_to_exclude = ["xml", "html", 
            *CaseDocument().get_all_text_fields(['casebody_data', 'text'], 'text', \
                ignore=['text.opinions.extracted_citations', 'text.opinions.type'])]

        if self.is_full_case_request():
            data_formats_to_exclude = ["text", "html", "xml"]

            try:
                data_formats_to_exclude.remove(self.request.query_params.get('body_format', 'text'))
            except ValueError:
                # defaults to sending text if it's a full case request with no body_format specified.
                data_formats_to_exclude.remove('text')

        source_filter = {
            "excludes": ["casebody_data.%s" % format for format in data_formats_to_exclude],
        }

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

        return super(CaseDocumentViewSet, self).retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        # cites_to can contain citations or IDs, so split out IDs into separate
        # cites_to_id parameter
        if 'cites_to' in request.query_params:
            request._request.GET = params = request._request.GET.copy()
            cites_to, cites_to_id = partition(lambda c: c.isdigit(), params.getlist('cites_to'))
            params.setlist('cites_to', cites_to)
            params.setlist('cites_to_id', cites_to_id)

        return super(CaseDocumentViewSet, self).list(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        """Set content-disposition for json and csv formats."""
        response = super().finalize_response(request, response, *args, **kwargs)
        if isinstance(response, Response):
            if response.status_code >= 400:
                # use text/plain for csv errors or else browser hides them:
                if response.accepted_renderer.format == 'csv':
                    response.content_type = "text/plain"
            elif response.accepted_renderer.format in ("csv", "json"):
                response["Content-Disposition"] = f'attachment; filename="CAP_{datetime.now()}.{response.accepted_renderer.format}"'
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
    def query_params_are_filters(query_body):
        # check if the queries are expected filter inputs to the cases API.    
        additional_filter_fields = CaseDocumentViewSet().valid_query_fields

        modifier_patterns = [r'__exclude$', r'__in$', r'__gt$', r'__gte$', r'__lt$', r'__lte$',
            r'^cites_to__', r'^author__']

        for key in query_body:
            for pattern in modifier_patterns:
                key = re.sub(pattern, '', key)

            if key not in CaseDocumentViewSet.filter_fields \
                and key not in CaseDocumentViewSet.search_nested_fields \
                and key not in additional_filter_fields:
                return (False, f'{key} is not a valid API parameter.')

        return (True, True)


    def get_query_data_from_api_query(self, q):
        # given an `api(...)` query, return a structured list of filters and aggregations
        # validate whether a case ID exists in the corpus
        # check if the supplied item is a valid case id
        if not q or not (q.startswith('api(') and q.endswith(')')):
            return (False, False)
    
        query_body = None
        try:
            query_body = QueryDict(q[4:-1], mutable=True)
        except Exception:
            return (False, 'Query is not in a URL parameter format.')

        err, msg = self.query_params_are_filters(query_body)
        if not err:
            return (False, msg)

        query_body['page_size'] = 1
        query_body['facet'] = 'decision_date'

        return (query_body, False)

    @staticmethod
    def create_timeline_entries(bucket_entries, total_dict, jurisdiction):
        # generate timeline datapoint given an elasticsearch query result
        years_out = []

        for year, count in bucket_entries.items():
            total = 0
            if jurisdiction == 'total':
                total = total_dict[year]
            else:
                total = total_dict[jurisdiction][year]

            years_out.append({
                "year": str(year),
                "count": [count, total],
                "doc_count": [count, total]
            })

        years_out.sort(key=lambda y: y["year"])
        return years_out

    @cache_func(
        key=lambda self, request: 'trends_es_case_counts',
        timeout=24*60*60,
    )
    def get_total_dict(self, request):
        # get and cache total dictionary. 
        total_query_dict = QueryDict('page_size=1&facet=decision_date&facet=jurisdiction,decision_date', mutable=True)

        total_results = api_request(request, CaseDocumentViewSet, 'list', get_params=total_query_dict).data

        return {
            **total_results['facets']['jurisdiction,decision_date'],
            **total_results['facets']['decision_date']
        }

    def get_citation_data(self, request, query_params, words_encoded):
        # given a case and its decision year, generate the timeline for the trends API.

        # parse jurisdiction
        jurisdiction = request.GET.getlist('jurisdiction')
        jurisdiction = jurisdiction[0].strip() if jurisdiction else 'total'
        if jurisdiction == '*':
            query_params['facet'] = 'jurisdiction,decision_date'
        elif jurisdiction != 'total':
            query_params['jurisdiction'] = jurisdiction

        # set up request caller and make API requests with facet parameter
        # These queries should always return valid JSON
        query_results = api_request(request, CaseDocumentViewSet, 'list', get_params=query_params).data

        # fail if there are no results. There should be _something_ in the page results if 
        # the aggregation is not just 0
        if 'results' not in query_results or not query_results['results']:
            return {}

        total_dict = self.get_total_dict(request)

        # variables for output storage
        results = {}
        out = {}

        # format results into trend graph
        if jurisdiction != '*':
            query_results = query_results['facets']['decision_date']
            years_out = self.create_timeline_entries(query_results, total_dict, jurisdiction)

            out[jurisdiction] = years_out
            results[words_encoded] = out
        else:
            query_results = query_results['facets']['jurisdiction,decision_date']

            for jurisdiction, value in list(query_results.items())[:10]:
                years_out = self.create_timeline_entries(value, total_dict, jurisdiction)
                out[jurisdiction] = years_out
            
            results[words_encoded] = out

        return results

    def list(self, request, *args, **kwargs):
        # without specific ngram search, return nothing
        q = self.request.GET.get('q', '').strip()
        if not q:
            return Response({})

        # check if we're querying for a case as opposed to a word
        # default to keyword search if value is empty 
        api_query_body, err_msg = self.get_query_data_from_api_query(q)

        # prepend word count as first byte. only applicable for n-grams
        words = q.lower().split(' ')[:3]  # use first 3 words
        q_len = len(words)
        q_sig = bytes([q_len]) + ' '.join(words).encode('utf8')

        if api_query_body and not err_msg:
            results = self.get_citation_data(request, api_query_body, q)
            pairs = []
        elif not api_query_body and err_msg:
            raise ValidationError({"error": err_msg})
        elif q_sig.endswith(b' *'):
            results = {}
            # wildcard search
            pairs = ngram_kv_store_ro.get_prefix(q_sig[:-1], packed=True)
        else:
            results = {}
            # non-wildcard search
            value = ngram_kv_store_ro.get(q_sig, packed=True)
            if value:
                pairs = [(q_sig, value)]
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
                        years_out.append({
                            "year": str(year) if year else "total",
                            "count": [count, totals[0]],
                            "doc_count": [doc_count, totals[1]]
                        })

                    years_out.sort(key=lambda y: y["year"])
                    out[jur_slug] = years_out

                if out:
                    results[gram[1:].decode('utf8')] = out

        paginated = {
            "count": len(results),
            "next": None,
            "previous": None,
            "results": results
        }

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
