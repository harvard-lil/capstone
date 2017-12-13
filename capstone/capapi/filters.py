import rest_framework_filters as filters
from capdb import models


class JurisdictionFilter(filters.FilterSet):
    class Meta:
        model = models.Jurisdiction
        fields = ('name', 'slug', 'name_long',)
        ordering_fields = ('name')

class CaseFilter(filters.FilterSet):
    name = filters.CharFilter(
        name='name',
        label='Name',
        lookup_expr='iexact')
    name_abbreviation = filters.CharFilter(
        name='name_abbreviation',
        label='Name Abbreviation',
        lookup_expr='iexact')
    citation = filters.CharFilter(
        name='citations',
        label='Citation',
        method='find_by_citation')
    court_name = filters.CharFilter(
        name='court__name',
        label='Court Name',
        lookup_expr='iexact')
    reporter_name = filters.CharFilter(
        name='reporter__full_name',
        label='Reporter Name',
        lookup_expr='iexact')
    jurisdiction = filters.CharFilter(
        name='jurisdiction__name',
        label='Jurisdiction Abbreviation',
        lookup_expr='iexact')
    jurisdiction_name = filters.CharFilter(
        name='jurisdiction__name_long',
        label='Jurisdiction Name',
        lookup_expr='iexact')
    decision_date_min = filters.CharFilter(
        label='Date Min (Format YYYY-MM-DD)',
        name='decision_date_min',
        method='find_by_date')
    decision_date_max = filters.CharFilter(
        label='Date Max (Format YYYY-MM-DD)',
        name='decision_date_max',
        method='find_by_date')

    def find_by_citation(self, qs, name, value):
        citation = models.Citation.objects.filter(cite__iexact=value)
        return qs.filter(citations=citation)

    def find_by_date(self, qs, name, value):
        if '_min' in name:
            return qs.filter(decision_date__gte=value)
        else:
            return qs.filter(decision_date__lte=value)

    class Meta:
        model = models.CaseMetadata
        fields = ['citation',
                  'slug',
                  'name',
                  'name_abbreviation',
                  'court_name',
                  'reporter_name',
                  'decision_date_min',
                  'decision_date_max',
                  'jurisdiction',
                  'jurisdiction_name',
                  'docket_number']


