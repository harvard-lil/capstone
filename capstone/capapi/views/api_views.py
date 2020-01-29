import bisect
import re
import urllib
from collections import OrderedDict, defaultdict
from functools import reduce
from pathlib import Path
from rest_framework import viewsets, renderers, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django_elasticsearch_dsl_drf.constants import LOOKUP_FILTER_RANGE, LOOKUP_QUERY_IN, LOOKUP_QUERY_GT, \
    LOOKUP_QUERY_GTE, LOOKUP_QUERY_LT, LOOKUP_QUERY_LTE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, IdsFilterBackend, \
    OrderingFilterBackend, DefaultOrderingFilterBackend, SimpleQueryStringSearchFilterBackend, HighlightBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet

from django.http import HttpResponseRedirect, FileResponse
from django.template import loader

from capapi import serializers, filters, permissions, renderers as capapi_renderers
from capapi.documents import CaseDocument
from capapi.pagination import CapESCursorPagination
from capapi.serializers import CaseDocumentSerializer
from capapi.middleware import add_cache_header
from capdb import models
from capdb.models import Citation
from capdb.storages import ngram_kv_store_ro
from user_data.models import UserHistory


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


class CitationViewSet(BaseViewSet):
    serializer_class = serializers.CitationWithCaseSerializer
    queryset = models.Citation.objects.order_by('pk')


class CAPFiltering(FilteringFilterBackend):
    def get_filter_query_params(self, request, view):
        def lc_values(values):
            return [value.lower() for value in values if isinstance(value, str)]

        def tokenize(filter_values):
            # takes each entry in filter_values and splits them on non alphanumeric characters into separate entries
            output = reduce(
                lambda tokenized_list, current_term: tokenized_list + re.split(r'[^a-zA-Z0-9]', current_term),
                filter_values, [])
            return(output)

        query_params = super().get_filter_query_params(request, view)
        if 'cite' in query_params:
            query_params['cite']['values'] = [Citation.normalize_cite(cite) for cite in
                                              lc_values(query_params['cite']['values']) ]

        if 'court_id' in query_params:
            query_params['court_id']['values'] = [ court_id for court_id
                                                   in query_params['court_id']['values'] if court_id.isdigit() ]
            if len(query_params['court_id']['values']) < 1:
                del query_params['court_id']

        if 'name' in query_params:
            query_params['name']['values'] = lc_values(tokenize(query_params['name']['values']))
            query_params['name']['lookup'] = 'in'

        if 'name_abbreviation' in query_params:
            query_params['name_abbreviation']['values'] = lc_values(tokenize(query_params['name_abbreviation']['values']))
            query_params['name_abbreviation']['lookup'] = 'in'

        if 'court' in query_params:
            query_params['court']['values'] = lc_values(query_params['court']['values'])

        if 'jurisdiction' in query_params:
            query_params['jurisdiction']['values'] = lc_values(query_params['jurisdiction']['values'])

        if 'docket_number' in query_params:
            query_params['docket_number']['values'] = lc_values(tokenize(query_params['docket_number']['values']))

        return query_params

    def to_html(self, request, queryset, view):
        """ This makes the html that goes inside the filters modal in the browsable API. Returns HTML string."""

        query_params = self.get_filter_query_params(request, view)
        filter_values = { param_name: param_data['values'] for param_name, param_data in query_params.items() }

        # this is for the content of the dropdown menus for jurisdiction, court, and reporter
        options = {}
        options['jurisdiction'] = [ {
                'value': jurisdiction[0],
                'label': jurisdiction[1],
                'selected': 'selected' if 'jurisdiction' in filter_values
                                          and jurisdiction[0] in filter_values['jurisdiction'] else ''
                }
            for jurisdiction in filters.jur_choices]

        options['court'] = [ {
                'value': court[0],
                'label': court[1],
                'selected': 'selected' if 'court' in filter_values and court[0] in filter_values['court'] else ''
                }
            for court in filters.court_choices]
        options['reporter'] = [{
            'value': str(reporter[0]),
            'label': reporter[1],
            'selected': 'selected' if 'reporter' in filter_values
                                      and str(reporter[0]) in filter_values['reporter'] else ''
            }
            for reporter in filters.reporter_choices]

        # For fields that look better with custom labels
        labels = {
                  'reporter': 'Reporter Series',
                  'decision_date_min': 'Earliest Decision Date (Format YYYY-MM-DD)',
                  'decision_date_max': 'Latest Decision Date (Format YYYY-MM-DD)',
                  'cite': 'Citation',
                  'docket_number': 'Docket Number (contains)',
                  'id': 'ID',
                  'court_id': 'Court ID'
                  }

        # this creates a dictionary that holds each field and data about it
        fields = OrderedDict()
        fields['cite']= {}
        fields['name_abbreviation']= {}
        fields['jurisdiction']= {}
        fields['reporter']= {}
        fields['decision_date_min']= {}
        fields['decision_date_max']= {}
        fields['docket_number']= {}
        fields['court']= {}
        fields['court_id']= {}
        fields['search']= {}
        fields['full_case']= {}
        fields['body_format']= {}

        for f in view.filter_fields:
            if f not in fields:
                if f == 'decision_date' or f == 'id' or f == 'name':
                    continue
                fields[f] = {}

            fields[f]['id'] = f

            if f.endswith('id'):
                fields[f]['type'] = 'number'
                fields[f]['step'] = 'any'
            elif f not in options:
                fields[f]['type'] = 'text'

            if f in options:
                fields[f]['options'] = options[f]
            else:
                fields[f]['value'] = ''

            if f in filter_values:
                fields[f]['value'] = ' '.join(filter_values[f])

            fields[f]['label'] = labels[f] if f in labels else f.replace('_', ' ').title()

        # full_case and body_format aren't part of the filters so I add them separately
        full_case = True if 'full_case' in request.GET and request.GET['full_case'] != '' else False
        fields['full_case'] = {
            'id': 'full_case',
            'label': 'Include full case text or just metadata?',
            'options': [
                {'value': 'true',
                 'label': 'Full case text',
                 'selected': 'selected' if  full_case else '',
                 },
                {'value': '',
                 'label': 'Just metadata (default)',
                 'selected': '' if  full_case else 'selected',
                 }]
        }

        body_format = request.GET['body_format'] if 'body_format' in request.GET else ''
        fields['body_format'] = {
            'id': 'body_format',
            'label': 'Format for case text (applies only if including case text):',
            'options': [
                {'value': 'text',
                 'label': 'Text Only (default)',
                 'selected': 'selected' if body_format == 'text' or body_format == '' else '',
                 },
                {'value': 'html',
                 'label': 'HTML',
                 'selected': 'selected' if body_format == 'html' else '',
                 },
                {'value': 'xml',
                 'label': 'XML',
                 'selected': 'selected' if body_format == 'xml' else '',
                 }]
        }

        # search is also separate from a filter, so it needs to be added separately
        fields['search'] = {
            'id': 'search',
            'value': request.query_params.get('search', ''),
            'label': 'Full-Text Search',
            'type': 'search'
        }

        template = loader.get_template('rest_framework/filters/cases.html')
        return template.render({'fields': fields })

class CAPFTSFilter(SimpleQueryStringSearchFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # ignores empty searches
        if 'search' in request.GET and request.GET['search'] is not '':
            queryset = super().filter_queryset(request, queryset, view)
        return queryset

    search_param = 'search'

class CAPOrderingFilterBackend(OrderingFilterBackend):
    @classmethod
    def transform_ordering_params(cls, ordering_params, ordering_fields):
        # changes relevance to -relevance (and vice versa) to avoid the rather unintuitive reverse-relevance sort
        # when sort=relevance
        return super(OrderingFilterBackend, cls).transform_ordering_params(
            ['relevance' if sort == '-relevance' else '-relevance' if sort == 'relevance' else sort for sort in ordering_params],
            ordering_fields)

class CaseDocumentViewSet(BaseDocumentViewSet):

    """The CaseDocument view."""

    # this lets DRF handle 'not found' issues the way they they are with the DB back end
    ignore = [404]

    document = CaseDocument
    serializer_class = CaseDocumentSerializer
    pagination_class = CapESCursorPagination

    renderer_classes = (
        renderers.JSONRenderer,
        capapi_renderers.BrowsableAPIRenderer,
        capapi_renderers.XMLRenderer,
        capapi_renderers.HTMLRenderer,
    )

    lookup_field = 'id'

    filter_backends = [
        CAPFTSFilter, # Facilitates FTS
        CAPFiltering, # Facilitates Filtering (Filters)
        IdsFilterBackend, # Filtering based on IDs
        CAPOrderingFilterBackend, # Orders Document
        HighlightBackend, # for search preview
        DefaultOrderingFilterBackend # Must be last
    ]

    # Define search fields
    simple_query_string_search_fields = (
        'name',
        'name_abbreviation.suggest',
        'jurisdiction.name_long',
        'court.name',
        # these are included in head_matter or text:
        # 'casebody_data.text.attorneys',
        # 'casebody_data.text.judges',
        # 'casebody_data.text.parties',
        'casebody_data.text.head_matter',
        'casebody_data.text.opinions.author',
        'casebody_data.text.opinions.text',
        'casebody_data.text.opinions.type',
        'casebody_data.text.corrections',
        'docket_number',
    )
    simple_query_string_options = {
        "default_operator": "and",
    }

    # Define filter fields
    filter_fields = {
        'id': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'name': 'name',
        'name_abbreviation': 'name_abbreviation',
        'court': 'court.slug',
        'court_id': 'court.id',
        'reporter': 'reporter.id',
        'jurisdiction': 'jurisdiction.slug',
        'docket_number': 'docket_number',
        'cite': 'citations.normalized_cite',
        'decision_date': 'decision_date',
        'decision_date_min': {'field': 'decision_date', 'default_lookup': 'gte'},
        'decision_date_max': {'field': 'decision_date', 'default_lookup': 'lte'},
    }

    # Define ordering fields
    ordering_fields = {
        'relevance': '_score',
        'decision_date': 'decision_date',
        'name_abbreviation': 'name_abbreviation.raw',
        'id': 'id',
    }
    # Specify default ordering. Relevance is a synonym for score, so we reverse it. It's reversed in the user-specified
    # ordering backend.
    ordering = ('-relevance', 'decision_date', 'id')

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
            data_formats_to_exclude = ["text",  "html", "xml"]

            try:
                data_formats_to_exclude.remove(self.request.query_params.get('body_format', 'text'))
            except ValueError:
                # defaults to sending text if it's a full case request with no body_format specified.
                data_formats_to_exclude.remove('text')

            source_filter = {"excludes": ["casebody_data.%s" % format for format in data_formats_to_exclude]}
        else:
            source_filter = {"excludes": "casebody_data.*"}

        return queryset.source(source_filter)

    def retrieve(self, *args, **kwargs):
        # for user's convenience, if user gets /cases/casecitation or /cases/Case Citation (or any non-numeric value)
        # we redirect to /cases/?cite=casecitation
        id = kwargs[self.lookup_field]
        if re.search(r'\D', id):
            normalized_cite = Citation.normalize_cite(id)
            query_string = urllib.parse.urlencode(dict(self.request.query_params, cite=normalized_cite), doseq=True)
            new_url = reverse('cases-list') + "?" + query_string
            return HttpResponseRedirect(new_url)

        return super(CaseDocumentViewSet, self).retrieve(*args, **kwargs)


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

    def list(self, request, *args, **kwargs):
        # without specific ngram search, return nothing
        q = self.request.GET.get('q', '').strip().lower()
        if not q:
            return Response({})

        ## look up query in KV store
        words = q.split(' ')[:3]  # use first 3 words
        q_len = len(words)
        # prepend word count as first byte
        q = bytes([q_len]) + ' '.join(words).encode('utf8')
        if q.endswith(b' *'):
            # wildcard search
            pairs = ngram_kv_store_ro.get_prefix(q[:-1], packed=True)
        else:
            # non-wildcard search
            value = ngram_kv_store_ro.get(q, packed=True)
            if value:
                pairs = [(q, value)]
            else:
                pairs = []

        ## format results
        results = OrderedDict()
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
