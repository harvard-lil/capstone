from functools import lru_cache

from django.utils.functional import SimpleLazyObject
from django.contrib.postgres.search import SearchQuery

import rest_framework_filters as filters

from capdb import models


# lazy load and cache choices so we don't get an error if this file is imported when database tables don't exist yet
def lazy_choices(queryset, id_attr, label_attr):
    @lru_cache(None)
    def get_choices():
        return queryset.order_by(label_attr).values_list(id_attr, label_attr)
    return SimpleLazyObject(get_choices)
jur_choices = lazy_choices(models.Jurisdiction.objects.all(), 'slug', 'name_long')
court_choices = lazy_choices(models.Court.objects.all(), 'slug', 'name')
reporter_choices = lazy_choices(models.Reporter.objects.all(), 'id', 'full_name')


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


class CourtFilter(filters.FilterSet):
    jurisdiction = filters.ChoiceFilter(
        field_name='jurisdiction__slug',
        choices=jur_choices)
    name = filters.CharFilter(lookup_expr='icontains', label='Name (contains)')

    class Meta:
        model = models.Court
        fields = [
            'slug',
            'name',
            'name_abbreviation',
            'jurisdiction'
        ]


class CaseFilter(filters.FilterSet):
    name_abbreviation = filters.CharFilter(
        field_name='name_abbreviation',
        label='Name Abbreviation (contains)',
        lookup_expr='icontains')
    cite = filters.CharFilter(
        field_name='cite',
        label='Citation',
        method='find_by_citation')
    court = filters.ChoiceFilter(
        field_name='court_slug',
        label='Court',
        choices=court_choices)
    reporter = filters.ChoiceFilter(
        field_name='reporter_id',
        label='Reporter',
        choices=reporter_choices)
    jurisdiction = filters.ChoiceFilter(
        field_name='jurisdiction_slug',
        label='Jurisdiction',
        choices=jur_choices)
    decision_date_min = filters.CharFilter(
        label='Date Min (Format YYYY-MM-DD)',
        field_name='decision_date_min',
        method='find_by_date')
    decision_date_max = filters.CharFilter(
        label='Date Max (Format YYYY-MM-DD)',
        field_name='decision_date_max',
        method='find_by_date')
    docket_number = filters.CharFilter(
        field_name='docket_number',
        label='Docket Number (contains)',
        lookup_expr='icontains')
    search = filters.CharFilter(
        field_name='tsvector',
        label='Full-Text Search',
        method='full_text_search_simple')


    # These aren't really filters, but are used elsewhere in preparing the response.
    # Included here so they'll show up in the UI.
    full_case = filters.ChoiceFilter(
        method='noop',
        label='Include full case text or just metadata?',
        choices=(('', 'Just metadata (default)'), ('true', 'Full case text')),
    )
    body_format = filters.ChoiceFilter(
        method='noop',
        label='Format for case text (applies only if including case text)',
        choices=(('text', 'text only (default)'), ('html', 'HTML'), ('xml', 'XML')),
    )

    def noop(self, qs, name, value):
        """ Not really a filter -- do nothing. """
        return qs

    def find_by_citation(self, qs, name, value):
        return qs.filter(citations__normalized_cite__exact=models.Citation.normalize_cite(value))

    def find_by_date(self, qs, name, value):
        if '_min' in name:
            return qs.filter(decision_date__gte=value)
        else:
            return qs.filter(decision_date__lte=value)

    def full_text_search_simple(self, qs, name, value):
        return qs.filter(tsvector=SearchQuery(value))

    class Meta:
        model = models.CaseMetadata
        fields = [
                  'cite',
                  'name_abbreviation',
                  'jurisdiction',
                  'reporter',
                  'decision_date_min',
                  'decision_date_max',
                  'docket_number',
                  ]


class CaseExportFilter(filters.FilterSet):
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

    def noop(self, qs, name, value):
        """ Not really a filter -- do nothing. """
        return qs
