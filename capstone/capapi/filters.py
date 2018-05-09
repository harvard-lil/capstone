from functools import lru_cache

from django.utils.functional import SimpleLazyObject
from django.utils.text import slugify
import rest_framework_filters as filters

from capdb import models

# lazy load jur_choices so we don't get an error if this file is imported when database tables don't exist yet
@lru_cache(None)
def get_jur_choices():
    return [(jur.id, jur.name) for jur in models.Jurisdiction.objects.all()]
jur_choices = SimpleLazyObject(get_jur_choices)


class JurisdictionFilter(filters.FilterSet):
    whitelisted = filters.BooleanFilter()
    id = filters.ChoiceFilter(choices=jur_choices, label='Name')
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
    jurisdictions = filters.MultipleChoiceFilter(choices=jur_choices)
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
    jurisdiction = filters.ChoiceFilter(choices=jur_choices)
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
    court_name = filters.CharFilter(
        field_name='court__name',
        label='Court Name (contains)',
        lookup_expr='icontains')
    reporter_name = filters.CharFilter(
        field_name='reporter__full_name',
        label='Reporter Name (contains)',
        lookup_expr='icontains')
    jurisdiction = filters.ChoiceFilter(choices=jur_choices)
    decision_date_min = filters.CharFilter(
        label='Date Min (Format YYYY-MM-DD)',
        field_name='decision_date_min',
        method='find_by_date')
    decision_date_max = filters.CharFilter(
        label='Date Max (Format YYYY-MM-DD)',
        field_name='decision_date_max',
        method='find_by_date')

    def find_by_citation(self, qs, name, value):
        return qs.filter(citations__normalized_cite__exact=slugify(value))

    def find_by_date(self, qs, name, value):
        if '_min' in name:
            return qs.filter(decision_date__gte=value)
        else:
            return qs.filter(decision_date__lte=value)

    class Meta:
        model = models.CaseMetadata
        fields = [
                  'cite',
                  'name_abbreviation',
                  'jurisdiction',
                  'reporter_name',
                  'decision_date_min',
                  'decision_date_max',
                  ]


