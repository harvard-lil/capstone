

import rest_framework_filters as filters
from capdb import models

jur_choices = [(jur.id, jur.name) for jur in models.Jurisdiction.objects.all()]


class JurisdictionFilter(filters.FilterSet):
    whitelisted = filters.BooleanFilter()
    id = filters.ChoiceFilter(choices=jur_choices, label='Name')
    name_long = filters.CharFilter(label='Long Name')

    class Meta:
        model = models.Jurisdiction
        fields = [
            'id',
            'name_long',
            'whitelisted',
            'slug',
        ]


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
    cite = filters.CharFilter(
        field_name='cite',
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
    jurisdiction = filters.ChoiceFilter(choices=jur_choices, label='jurisdiction')
    decision_date_min = filters.CharFilter(
        label='Date Min (Format YYYY-MM-DD)',
        field_name='decision_date_min',
        method='find_by_date')
    decision_date_max = filters.CharFilter(
        label='Date Max (Format YYYY-MM-DD)',
        field_name='decision_date_max',
        method='find_by_date')

    def find_by_citation(self, qs, name, value):
        return qs.filter(citations__normalized_cite__exact=value)

    def find_by_date(self, qs, name, value):
        if '_min' in name:
            return qs.filter(decision_date__gte=value)
        else:
            return qs.filter(decision_date__lte=value)

    class Meta:
        model = models.CaseMetadata
        fields = [
                  'cite',
                  'name',
                  'name_abbreviation',
                  'jurisdiction',
                  'court_name',
                  'court_slug',
                  'reporter_name',
                  'decision_date_min',
                  'decision_date_max',
                  'docket_number',
                  ]


