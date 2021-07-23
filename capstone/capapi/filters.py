from copy import copy
from functools import lru_cache, reduce
import asyncio
import operator
import six
import uuid

from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django_elasticsearch_dsl_drf.constants import MATCHING_OPTION_MUST, MATCHING_OPTION_SHOULD
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, SimpleQueryStringSearchFilterBackend, \
    OrderingFilterBackend, FacetedSearchFilterBackend, BaseSearchFilterBackend
from django_elasticsearch_dsl_drf.filter_backends.search.query_backends import NestedQueryBackend, SimpleQueryStringQueryBackend
from django_filters.rest_framework import filters, DjangoFilterBackend, FilterSet
from django_filters.utils import translate_validation
from django.http import QueryDict, HttpRequest
from elasticsearch import AsyncElasticsearch, Elasticsearch
from elasticsearch_dsl.query import Q
from rest_framework.exceptions import ValidationError
from urllib.parse import urlencode

from capdb import models
from scripts.helpers import normalize_cite
from scripts.extract_cites import extract_citations_normalized
from user_data.models import UserHistory
from capapi.views import api_views

### HELPERS ###

# lazy load and cache choices so we don't get an error if this file is imported when database tables don't exist yet


def lazy_choices(queryset, id_attr, label_attr):
    @lru_cache(None)
    def get_choices():
        return queryset.order_by(label_attr).values_list(id_attr, label_attr)
    return SimpleLazyObject(get_choices)
jur_choices = lazy_choices(models.Jurisdiction.objects.all(), 'slug', 'name_long')
court_choices = lazy_choices(models.Court.objects.all(), 'slug', 'name')
reporter_choices = lazy_choices(models.Reporter.objects.all(), 'id', 'short_name')
analysis_fields = ['word_count', 'char_count', 'ocr_confidence', 'pagerank.percentile', 'pagerank.raw', 'simhash', 'sha256', 'cardinality']


class NoopMixin():
    """
        Mixin to allow method='noop' in filters.
    """
    def noop(self, qs, name, value):
        return qs

### FILTERS ###

class JurisdictionFilter(FilterSet):
    whitelisted = filters.BooleanFilter()
    slug = filters.ChoiceFilter(choices=jur_choices, label='Name')
    name_long = filters.CharFilter(label='Long Name')

    class Meta:
        model = models.Jurisdiction
        fields = [
            'id',
            'name',
            'name_long',
            'whitelisted',
            'slug',
        ]


class ReporterFilter(FilterSet):
    jurisdictions = filters.MultipleChoiceFilter(
        field_name='jurisdictions__slug',
        choices=jur_choices)
    full_name = filters.CharFilter(lookup_expr='icontains', label='Full Name (contains)')

    class Meta:
        model = models.Reporter
        fields = [
            'jurisdictions',
            'full_name',
            'short_name',
            'start_year',
            'end_year',
            'volume_count'
        ]


class VolumeFilter(FilterSet):
    jurisdictions = filters.MultipleChoiceFilter(
        label='Jurisdiction',
        field_name='reporter__jurisdictions__slug',
        choices=jur_choices)

    reporter = filters.MultipleChoiceFilter(
        field_name='reporter',
        choices=reporter_choices)

    volume_number = filters.NumberFilter(field_name='volume_number')
    publication_year = filters.NumberFilter(field_name='publication_year')

    class Meta:
        model = models.VolumeMetadata
        fields = [
            'reporter',
            'jurisdictions',
            'volume_number',
            'publication_year',
        ]


class CourtFilter(FilterSet):
    jurisdiction = filters.ChoiceFilter(
        field_name='jurisdiction__slug',
        choices=jur_choices)
    name = filters.CharFilter(lookup_expr='icontains', label='Name (contains)')

    class Meta:
        model = models.Court
        fields = [
            'id',
            'slug',
            'name',
            'name_abbreviation',
            'jurisdiction'
        ]


class CaseExportFilter(NoopMixin, FilterSet):
    with_old = filters.ChoiceFilter(
        field_name='with_old',
        label='Include previous versions of files?',
        choices=(('true', 'Include previous versions of files'), ('false', 'Only include newest version of each file')),
        method='noop',  # handled by CaseExportViewSet.filter_queryset()
    )

    class Meta:
        model = models.CaseExport
        fields = {
            'body_format': ['exact'],
            'filter_type': ['exact'],
            'filter_id': ['exact'],
        }


class NgramFilter(FilterSet):
    q = filters.CharFilter(
        label='Words',
        help_text='Up to three words separated by spaces',
    )
    jurisdiction = filters.MultipleChoiceFilter(
        label='Jurisdiction',
        choices=SimpleLazyObject(lambda: [['total', 'Total across jurisdictions (default)'], ['*', 'Select all jurisdictions']] + list(jur_choices)),
    )
    year = filters.CharFilter(
        label='Year filter',
    )

    class Meta:
        fields = ['q', 'jurisdiction', 'year']


class UserHistoryFilter(FilterSet):
    case_id = filters.NumberFilter()
    date = filters.DateTimeFromToRangeFilter()

    class Meta:
        model = UserHistory
        fields = ['case_id', 'date']


class CaseFilter(FilterSet):
    """
        Used for HTML display and validation, but not actual filtering.
        Rendered by CaseFilterBackend, which applies filters to the ES query.
    """
    search = filters.CharFilter(
        label='Full-Text Search',
        help_text='Search for words separated by spaces. All words are required in results. Words less than 3 characters are ignored.')
    cite = filters.CharFilter(label='Citation')
    name_abbreviation = filters.CharFilter(label='Name Abbreviation (contains)')
    name = filters.CharFilter(label='Full Name (contains)')
    jurisdiction = filters.ChoiceFilter(choices=jur_choices)
    reporter = filters.ChoiceFilter(choices=reporter_choices, label='Reporter Series')
    decision_date__gte = filters.CharFilter(label='Earliest Decision Date (Format YYYY-MM-DD)')
    decision_date__lte = filters.CharFilter(label='Latest Decision Date (Format YYYY-MM-DD)')
    docket_number = filters.CharFilter(label='Docket Number (contains)')
    court = filters.ChoiceFilter(choices=court_choices)
    court_id = filters.NumberFilter(label='Court ID')
    full_case = filters.ChoiceFilter(
        label='Include full case text or just metadata?',
        choices=(('false', 'Just metadata (default)'), ('true', 'Full case text')),
    )
    author = filters.CharFilter(
        label='Filter by opinion author'
        )
    author_disposition = filters.CharFilter(
        label='Filter by opinion author and their disposition in a ruling. Values must be separated by a colon; invalid input will be \
            ignored. Example: author_disposition=scalia:dissent.'
    )
    body_format = filters.ChoiceFilter(
        label='Format for case text (applies only if including case text)',
        choices=(('text', 'text only (default)'), ('html', 'HTML'), ('xml', 'XML'), ('tokens', 'debug tokens')),
    )
    cites_to = filters.CharFilter(label='Cases citing to citation (citation or case id)')
    cites_to_state = filters.CharFilter(label='Cases citing to cases in a state', field_name='cites_to', lookup_expr='state')
    facet = filters.CharFilter(label='Facet for which to aggregate results. Can be jurisdiction, \
        decision_date, or a comma-separated permutation of either.')
    ordering = filters.ChoiceFilter(
        label='Sort order (defaults to relevance, if search is provided, else decision_date)',
        choices=[
            ('relevance', 'Relevance'),
            ('decision_date', 'Decision date'),
            ('-decision_date', 'Reverse decision date'),
            ('name_abbreviation', 'Name abbreviation'),
            ('-name_abbreviation', 'Reverse name abbreviation'),
            ('id', 'id'),
            ('-id', 'Reverse id'),
            ('', '--- Analysis fields ---')
        ]+[choice for field in analysis_fields for choice in [[f'analysis.{field}', field], [f'-analysis.{field}', f'Reverse {field}']]],
    )
    page_size = filters.NumberFilter(min_value=1, max_value=10000, label='Results per page (1 to 10,000; default 100)')
    last_updated__gte = filters.CharFilter(label='last_updated greater than or equal to this prefix')
    last_updated__lte = filters.CharFilter(label='last_updated less than or equal to this prefix')

    class Meta:
        model = models.CaseMetadata
        fields = []


class CaseFilterBackend(FilteringFilterBackend, DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
            Apply form validation from DjangoFilterBackend.filter_queryset(), which uses the fields
             defined on CaseFilter, before applying actual filters from FilteringFilterBackend.
        """
        filterset = self.get_filterset(request, None, view)
        if not filterset.is_valid():
            raise translate_validation(filterset.errors)
        return super().filter_queryset(request, queryset, view)

    def get_filter_query_params(self, request, view):
        def lc_values(values):
            return [value.lower() for value in values if isinstance(value, str)]

        query_params = super().get_filter_query_params(request, view)

        if 'cite' in query_params:
            query_params['cite']['values'] = [normalize_cite(cite) for cite in lc_values(query_params['cite']['values'])]

        if 'court' in query_params:
            query_params['court']['values'] = lc_values(query_params['court']['values'])

        if 'jurisdiction' in query_params:
            query_params['jurisdiction']['values'] = lc_values(query_params['jurisdiction']['values'])

        if 'cites_to' in query_params:
            query_params['cites_to']['values'] = [normalize_cite(c) for c in query_params['cites_to']['values']]
        return query_params


class BaseFTSFilter(SimpleQueryStringSearchFilterBackend):
    """ Base filter for query params that search by simple_query_string. """
    def filter_queryset(self, request, queryset, view):
        # ignore empty searches
        if request.GET.get(self.search_param):
            # Patch simple_query_string_search_fields on the view, since SimpleQueryStringSearchFilterBackend isn't
            # set up to be used multiple times on the same view.
            view.simple_query_string_search_fields = self.fields
            return super().filter_queryset(request, queryset, view)
        return queryset


class NameFTSFilter(BaseFTSFilter):
    search_param = 'name'
    fields = ('name',)


class NameAbbreviationFTSFilter(BaseFTSFilter):
    search_param = 'name_abbreviation'
    fields = ('name_abbreviation',)


class DocketNumberFTSFilter(BaseFTSFilter):
    search_param = 'docket_number'
    fields = ('docket_number',)


class CitesToDynamicFilter(BaseFTSFilter):
    fields = ('id',)

    def get_search_fields(self, view, request):
        """
        Overridden methods to dynamically generate search fields.
        While powerful, do not allow users to query second degree citations to prevent exponential 
        performance costs.
        """
        return {f'cites_to__{field}':api_views.CaseDocumentViewSet.get_queryable_field_map()[field] for field 
                    in api_views.CaseDocumentViewSet.get_queryable_field_map() 
                    if not field.startswith('cites_to')}

    def deep_get(self, dictionary, keys, default=[]):
        """ https://stackoverflow.com/questions/25833613/safe-method-to-get-value-of-nested-dictionary """
        return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys, dictionary)

    def parallel_execute(self, request, max_workers=20, page_size=1000):
        """
        Execute queries in parallel. Return 20K results to temper cluster load.
        source: https://github.com/elastic/elasticsearch/issues/18829
        """

        # lists are thread-safe, so use this to store results.
        results = []

        async def fetch(es, worker_i, query_body):
            # Fetch data asynchronously
            # Unfortunately, the decorators of regular Elasticsearch() are not present 
            # So we have to shunt source / sort / pagination in ourselves.
            body = {
                **query_body,
                "from": page_size * worker_i,
                "size": page_size,
                "_source": "false",
                "sort": ["decision_date", "id"],
            }
            resp = await es.search(index='cases', body=body)
            results.append(self.deep_get(resp, ['hits','hits']))

        async def get_query_results(query_body):
            es = AsyncElasticsearch([settings.ELASTICSEARCH_DSL['default']['hosts']])

            await asyncio.gather(*[
                asyncio.ensure_future(fetch(es, i, query_body))
                for i in range(0, max_workers)
            ])

        view = api_views.CaseDocumentViewSet(request=request)
        search = view.filter_queryset(view.get_queryset())
        query_body = search.to_dict()
        
        loop = asyncio.new_event_loop()
        loop.run_until_complete(get_query_results(query_body))

        results = [item['_id'] for sublist in results for item in sublist if '_id' in item]
        return results


    def filter_queryset(self, request, queryset, view):
        # ignore empty searches
        search_fields = self.get_search_fields(view, request).copy()

        # reformat data as ELK query. no dictionary comprehension due to complexity and length
        cites_to_keys = {}
        for key, value in request.GET.items():
            if key in search_fields:
                cites_to_keys[key.split('cites_to__')[1]] = request.GET[key]

        # We can use a shell request because the view simply pulls parameters out.
        first_request = HttpRequest()
        first_request.query_params = QueryDict('', mutable=True)
        first_request.query_params.update(cites_to_keys)

        results = self.parallel_execute(first_request) if cites_to_keys else []

        if results:
            request.GET._mutable = True
            _ = [request.GET.pop(key) for key in search_fields if key in request.GET.keys()]
            request.GET.setlist('cites_to_id', results)
            request.GET._mutable = False

        if request.GET.get(self.search_param):
            # Patch simple_query_string_search_fields on the view, since SimpleQueryStringSearchFilterBackend isn't
            # set up to be used multiple times on the same view.
            view.simple_query_string_search_fields = self.fields
            return super().filter_queryset(request, queryset, view)
        return queryset


class NestedSimpleStringQueryBackend(NestedQueryBackend):
    """
    Support for SimpleStringQuery and highlighting for nested fields
    """
    @classmethod
    def prepare_highlight_fields(cls, view):
        highlight_fields = view.highlight_nested_fields if hasattr(view, 'highlight_nested_fields') else {}

        for field, options in highlight_fields.items():
            if 'enabled' not in highlight_fields[field]:
                highlight_fields[field]['enabled'] = False

            if 'options' not in highlight_fields[field]:
                highlight_fields[field]['options'] = {}

        return highlight_fields

    @classmethod
    def construct_search(cls, request, view, search_backend):
        if not hasattr(view, 'search_nested_fields'):
            return []

        query_params = search_backend.get_search_query_params(request)
        __queries = []

        query_operator = operator.or_
        if search_backend.matching == MATCHING_OPTION_MUST:
            query_operator = operator.and_

        for search_term in query_params:
            # Overload the `:` splitting in split_lookup_name to separate distinct fields.
            sub_search_terms = list(search_backend.split_lookup_name(search_term, 1).copy())

            queried_fields = []
            for label, options in view.search_nested_fields.items():
                queries = []
                path = options.get('path')

                for _field in options.get('fields', []):
                    field = "{}.{}".format(path, _field)

                    # if the field in this query is not explicitly specified by the filter
                    # or there is no more data left to pull from the parameter,
                    # continue
                    if field not in search_backend.nested_query_fields or not sub_search_terms:
                        continue

                    value = sub_search_terms[0]
                    if search_backend.separate_queries_per_field:
                        value = sub_search_terms.pop(0)

                    field_kwargs = {
                        "query": value,
                        "fields": [field],
                    }
                    queried_fields.append(field)

                    queries.append(
                        Q("simple_query_string", **field_kwargs)
                    )

                highlight_nested_fields = NestedSimpleStringQueryBackend.prepare_highlight_fields(view)
                highlight_inner = {'name':uuid.uuid4().hex.upper()[0:10], 'highlight': {'fields': {}}}
                for __field, __options in highlight_nested_fields.items():
                    if __field in queried_fields or __options['enabled']:
                        highlight_inner['highlight']['fields'][__field] = __options['options']
                
                __queries.append(
                    Q(
                        cls.query_type,
                        path=path,
                        query=six.moves.reduce(query_operator, queries),
                        inner_hits=highlight_inner
                    )
                )

        return __queries


class NestedFTSFilter(BaseSearchFilterBackend):
    """
    Filter to represent nested simple string queries
    """
    query_backends = [
        NestedSimpleStringQueryBackend,
    ]

    separate_queries_per_field = True
    matching = MATCHING_OPTION_MUST


class MultiFieldFTSFilter(BaseSearchFilterBackend):
    search_param = 'search'
    fields = (
        'name',
        'name_abbreviation',
        'jurisdiction.name_long',
        'court.name',
        'casebody_data.text.head_matter',
        'casebody_data.text.corrections',
        'docket_number',
    )

    nested_query_fields = (
        'casebody_data.text.opinions.author',
        'casebody_data.text.opinions.text',
    )

    query_backends = [
        NestedSimpleStringQueryBackend,
        SimpleQueryStringQueryBackend,
    ]

    separate_queries_per_field = False
    matching = MATCHING_OPTION_SHOULD

    """ Base filter for query params that search by simple_query_string. """
    def filter_queryset(self, request, queryset, view):
        # ignore empty searches
        if request.GET.get(self.search_param):
            # Patch simple_query_string_search_fields on the view, since SimpleQueryStringSearchFilterBackend isn't
            # set up to be used multiple times on the same view.
            view.simple_query_string_search_fields = self.fields
            return super().filter_queryset(request, queryset, view)
        return queryset


class AuthorDispositionFTSFilter(NestedFTSFilter):
    """
    Multi match search filter backend to query on author + disposition
    """
    search_param = 'author_disposition'
    nested_query_fields = ('casebody_data.text.opinions.author','casebody_data.text.opinions.type',)

    matching = MATCHING_OPTION_MUST


class AuthorFTSFilter(NestedFTSFilter):
    """
    Multi match search filter backend to query on author + disposition
    """
    search_param = 'author'
    nested_query_fields = ('casebody_data.text.opinions.author',)


class CAPOrderingFilterBackend(OrderingFilterBackend):
    # NOTE: ordering in Elasticsearch falls back to the "internal Lucene doc id" for a given shard,
    # which means it is stable as long as we have only one shard. If we add additional shards, we will
    # need to bind each user to a single shard for pagination.
    @classmethod
    def transform_ordering_params(cls, ordering_params, ordering_fields):
        # changes relevance to -relevance (and vice versa) to avoid the rather unintuitive reverse-relevance sort
        # when sort=relevance
        return super().transform_ordering_params(
            ['relevance' if sort == '-relevance' else '-relevance' if sort == 'relevance' else sort for sort in ordering_params],
            ordering_fields)


class CAPFacetedSearchFilterBackend(FacetedSearchFilterBackend):
    # The same as FacetedSearchFilterBackend, but with support for sub-aggregations.
    def construct_facets(self, request, view):
        """
        Construct facets structure.
        """    
        __facets = {}
        faceted_search_query_params = [item.split(',') for item in self.get_faceted_search_query_params(
            request
        )]
        faceted_search_query_params = [item for sublist in faceted_search_query_params for item in sublist]

        faceted_search_fields = self.prepare_faceted_search_fields(view)
        for __field, __options in faceted_search_fields.items():
            if __field in faceted_search_query_params or __options['enabled']:
                __facets.update(
                    {
                        __field: {
                            'facet': faceted_search_fields[__field]['facet'](
                                field=faceted_search_fields[__field]['field'],
                                **faceted_search_fields[__field]['options']
                            ),
                            'global': faceted_search_fields[__field]['global'],
                        }
                    }
                )
        return __facets    

    def aggregate(self, request, queryset, view):
        """
        Generate field aggregations. Supports 3 parallel aggs and 2 sub-aggregations
        """

        # If cursor is attached, don't aggregate
        query_params = request.query_params.copy()
        if query_params.getlist('cursor', []):
            return queryset

        # pull query_params as the order of the aggregations
        faceted_search_query_params = self.get_faceted_search_query_params(
            request
        )

        __facets = self.construct_facets(request, view)

        for i, __potential_field in enumerate(faceted_search_query_params[:3]):
            __fields = __potential_field.split(',')
            previous_agg_key = None

            for j, __field in enumerate(__fields[:2]): 
                __facet = __facets[__field]
                agg = __facet['facet'].get_aggregation()

                if previous_agg_key is None:
                    next_index = min(j + 1, len(__fields) - 1)
                    previous_agg_key = __field
                    if next_index == j + 1:
                        previous_agg_key += f',{__fields[next_index]}'

                    queryset.aggs.bucket(
                        previous_agg_key,
                        agg
                    )
                    queryset.aggs[previous_agg_key].pipeline('sortedbucketfield', 
                        'bucket_sort',
                        sort=[{'_count': {'order': 'desc'}}])
                else:
                    queryset.aggs[previous_agg_key].bucket(
                        __field,
                        agg
                    )
                    queryset.aggs[previous_agg_key][__field].pipeline('sortedbucketfield', 
                        'bucket_sort',
                        sort=[{'_count': {'order': 'desc'}}])

        return queryset


class ResolveFilter(FilterSet):
    """
        Used for HTML display and validation, but not actual filtering.
        Rendered by ResolveFilterBackend, which applies filters to the ES query.
    """
    q = filters.CharFilter(label='Citation', help_text='Citation, or text containing multiple citations')

    class Meta:
        model = models.CaseMetadata
        fields = []


class ResolveFilterBackend(FilteringFilterBackend, DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
            Apply form validation from DjangoFilterBackend.filter_queryset(), which uses the fields
             defined on ResolveFilter, before applying actual filters from FilteringFilterBackend.
        """
        filterset = self.get_filterset(request, None, view)
        if not filterset.is_valid():
            raise translate_validation(filterset.errors)
        return super().filter_queryset(request, queryset, view)

    def get_filter_query_params(self, request, view):
        query_params = super().get_filter_query_params(request, view)
        if not query_params:
            raise ValidationError("Query parameter 'q' is required")

        # extract cites from query string and build lookup of normalized cites -> matched text in query
        extracted_cites = {}
        for v in query_params['q']['values']:
            for cite_text, normalized_cite, rdb_normalized_cite in extract_citations_normalized(v):
                extracted_cites[normalized_cite] = cite_text
                extracted_cites[rdb_normalized_cite] = cite_text

        if not extracted_cites:
            raise ValidationError("No citations found in query.")
        query_params['q']['values'] = set(extracted_cites)

        # attach lookup to request so it can be used by ResolveDocumentListSerializer
        request.extracted_cites = extracted_cites

        return query_params
