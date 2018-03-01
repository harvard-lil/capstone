import rest_framework_filters as filters
from capdb import models


class JurisdictionFilter(filters.FilterSet):
    class Meta:
        model = models.Jurisdiction
        fields = ('name', 'slug', 'name_long',)
        ordering_fields = ('name')


class CourtFilter(filters.FilterSet):
    class Meta:
        model = models.Court
        fields = '__all__'


class CaseFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name='name',
        label='Name',
        lookup_expr='iexact')
    name_abbreviation = filters.CharFilter(
        field_name='name_abbreviation',
        label='Name Abbreviation',
        lookup_expr='iexact')
    citation = filters.CharFilter(
        field_name='citation',
        label='Citation',
        method='find_by_citation')
    court_slug = filters.CharFilter(
        field_name='court__slug',
        label='Court Slug',
        lookup_expr='iexact')
    court_name = filters.CharFilter(
        field_name='court__name',
        label='Court Name',
        lookup_expr='iexact')
    reporter_name = filters.CharFilter(
        field_name='reporter__full_name',
        label='Reporter Name',
        lookup_expr='iexact')
    jurisdiction = filters.CharFilter(
        field_name='jurisdiction__name',
        label='Jurisdiction Abbreviation',
        lookup_expr='iexact')
    jurisdiction_name = filters.CharFilter(
        field_name='jurisdiction__name_long',
        label='Jurisdiction Name',
        lookup_expr='iexact')
    decision_date_min = filters.CharFilter(
        label='Date Min (Format YYYY-MM-DD)',
        field_name='decision_date_min',
        method='find_by_date')
    decision_date_max = filters.CharFilter(
        label='Date Max (Format YYYY-MM-DD)',
        field_name='decision_date_max',
        method='find_by_date')
    judges = filters.CharFilter(field_name='judges', label='judges', lookup_expr='icontains')
    attorneys = filters.CharFilter(field_name='attorneys', label='attorneys', lookup_expr='icontains')
    parties = filters.CharFilter(field_name='parties', label='parties', lookup_expr='icontains')
    opinions = filters.CharFilter(field_name='opinions', label='opinions', lookup_expr='icontains')

    def find_by_citation(self, qs, name, value):
        return qs.filter(citation__cite__iexact=value)

    def find_by_date(self, qs, name, value):
        if '_min' in name:
            return qs.filter(decision_date__gte=value)
        else:
            return qs.filter(decision_date__lte=value)

    class Meta:
        model = models.CaseMetadata
        fields = [
                  'citation',
                  'name',
                  'name_abbreviation',
                  'court_name',
                  'court_slug',
                  'reporter_name',
                  'decision_date_min',
                  'decision_date_max',
                  'jurisdiction',
                  'jurisdiction_name',
                  'docket_number',
                  'judges',
                  'parties',
                  'opinions',
                  'attorneys'
                  ]


