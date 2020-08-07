from functools import lru_cache
import rest_framework_filters as filters

from django.utils.functional import SimpleLazyObject
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, SimpleQueryStringSearchFilterBackend, \
    OrderingFilterBackend
from elasticsearch.exceptions import NotFoundError
from rest_framework_filters.backends import RestFrameworkFilterBackend
from capapi.documents import CaseDocument
from capdb import models
from user_data.models import UserHistory


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


class NoopMixin():
    """
        Mixin to allow method='noop' in filters.
    """
    def noop(self, qs, name, value):
        return qs

### FILTERS ###

class JurisdictionFilter(filters.FilterSet):
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


class ReporterFilter(filters.FilterSet):
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


class VolumeFilter(filters.FilterSet):
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


class CourtFilter(filters.FilterSet):
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


class CaseExportFilter(NoopMixin, filters.FilterSet):
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


class NgramFilter(filters.FilterSet):
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


class UserHistoryFilter(filters.FilterSet):
    case_id = filters.NumberFilter()
    date = filters.DateTimeFromToRangeFilter()

    class Meta:
        model = UserHistory
        fields = ['case_id', 'date']


class CaseFilter(filters.FilterSet):
    """
        This is only used for HTML display; it is rendered by CaseFilterBackend, which applies filters to the ES query.
    """
    search = filters.CharFilter(
        label='Full-Text Search',
        help_text='Search for words separated by spaces. All words are required in results. Words less than 3 characters are ignored.')
    cite = filters.CharFilter(label='Citation')
    name_abbreviation = filters.CharFilter(label='Name Abbreviation (contains)')
    name = filters.CharFilter(label='Full Name (contains)')
    jurisdiction = filters.ChoiceFilter(choices=jur_choices)
    reporter = filters.ChoiceFilter(choices=reporter_choices, label='Reporter Series')
    decision_date_min = filters.CharFilter(label='Earliest Decision Date (Format YYYY-MM-DD)')
    decision_date_max = filters.CharFilter(label='Latest Decision Date (Format YYYY-MM-DD)')
    docket_number = filters.CharFilter(label='Docket Number (contains)')
    court = filters.ChoiceFilter(choices=court_choices)
    court_id = filters.NumberFilter(label='Court ID')
    full_case = filters.ChoiceFilter(
        label='Include full case text or just metadata?',
        choices=(('', 'Just metadata (default)'), ('true', 'Full case text')),
    )
    body_format = filters.ChoiceFilter(
        label='Format for case text (applies only if including case text)',
        choices=(('text', 'text only (default)'), ('html', 'HTML'), ('xml', 'XML'), ('tokens', 'debug tokens')),
    )
    cites_to = filters.CharFilter(label='Cases citing to citation (citation or case id)')
    ordering = filters.ChoiceFilter(
        label='Sort order',
        choices=(
            ('', 'Relevance, then decision date (default)'),
            ('decision_date', 'Decision date'),
            ('-decision_date', 'Reverse decision date'),
            ('name_abbreviation', 'Name abbreviation'),
            ('-name_abbreviation', 'Reverse name abbreviation'),
            ('id', 'id'),
            ('-id', 'Reverse id'),
        ),
    )
    page_size = filters.NumberFilter(label='Results per page (1 to 10,000; default 100)')
    last_updated_min = filters.CharFilter(label='last_updated greater than or equal to this prefix')
    last_updated_max = filters.CharFilter(label='last_updated less than or equal to this prefix')


class CaseFilterBackend(FilteringFilterBackend, RestFrameworkFilterBackend):
    def get_filter_query_params(self, request, view):
        def lc_values(values):
            return [value.lower() for value in values if isinstance(value, str)]

        def normalize_cites(values):
            return [models.normalize_cite(value) for value in values if isinstance(value, str)]

        query_params = super().get_filter_query_params(request, view)

        if 'cite' in query_params:
            query_params['cite']['values'] = [models.normalize_cite(cite) for cite in
                                              lc_values(query_params['cite']['values'])]

        if 'court_id' in query_params:
            query_params['court_id']['values'] = [court_id for court_id in
                                                  query_params['court_id']['values'] if court_id.isdigit()]
            if len(query_params['court_id']['values']) < 1:
                del query_params['court_id']

        if 'court' in query_params:
            query_params['court']['values'] = lc_values(query_params['court']['values'])

        if 'jurisdiction' in query_params:
            query_params['jurisdiction']['values'] = lc_values(query_params['jurisdiction']['values'])

        if 'cites_to' in query_params:
            query_params['cites_to']['values'] = normalize_cites(query_params['cites_to']['values'])
            for cite in query_params['cites_to']['values']:
                # check if case id is passed in
                if cite.isdigit():
                    try:
                        case = CaseDocument.get(id=cite)
                        # remove id from lookup
                        query_params['cites_to']['values'].remove(cite)
                        # add all citations relating to case
                        query_params['cites_to']['values'] += [c['normalized_cite'] for c in case.citations]
                    except NotFoundError:
                        pass
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


class MultiFieldFTSFilter(BaseFTSFilter):
    search_param = 'search'
    fields = (
        'name',
        'name_abbreviation',
        'jurisdiction.name_long',
        'court.name',
        'casebody_data.text.head_matter',
        'casebody_data.text.opinions.author',
        'casebody_data.text.opinions.text',
        'casebody_data.text.opinions.type',
        'casebody_data.text.corrections',
        'docket_number',
    )


class NameFTSFilter(BaseFTSFilter):
    search_param = 'name'
    fields = ('name',)


class NameAbbreviationFTSFilter(BaseFTSFilter):
    search_param = 'name_abbreviation'
    fields = ('name_abbreviation',)


class DocketNumberFTSFilter(BaseFTSFilter):
    search_param = 'docket_number'
    fields = ('docket_number',)


class CAPOrderingFilterBackend(OrderingFilterBackend):
    @classmethod
    def transform_ordering_params(cls, ordering_params, ordering_fields):
        # changes relevance to -relevance (and vice versa) to avoid the rather unintuitive reverse-relevance sort
        # when sort=relevance
        return super().transform_ordering_params(
            ['relevance' if sort == '-relevance' else '-relevance' if sort == 'relevance' else sort for sort in ordering_params],
            ordering_fields)
