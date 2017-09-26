import django_filters

from django_filters import rest_framework as filters
from capdb import models


class CaseFilter(filters.FilterSet):
    name = django_filters.CharFilter(name="name", lookup_expr='icontains')
    name_abbreviation = django_filters.CharFilter(name="name_abbreviation", lookup_expr='icontains')
    citation = django_filters.CharFilter(name="citation__cite", lookup_expr='icontains')
    court_name = django_filters.CharFilter(name="court__name", lookup_expr='icontains')
    reporter_name = django_filters.CharFilter(name="reporter__full_name", lookup_expr='icontains')
    jurisdiction_name = django_filters.CharFilter(name="jurisdiction__name", lookup_expr='icontains')
    decision_date = django_filters.DateFromToRangeFilter()


    class Meta:
        model = models.CaseMetadata
        fields = ['name', 'name_abbreviation', 'citation', 'court_name',
                  'reporter_name',
                  'decision_date',
                  'jurisdiction_name']


class JurisdictionFilter(filters.FilterSet):
    class Meta:
        model = models.Jurisdiction
        fields = '__all__'
