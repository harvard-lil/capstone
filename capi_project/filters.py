import django_filters
from .models import Case, Jurisdiction
from .serializers import CaseSerializer
from rest_framework import generics

class CaseFilter(django_filters.rest_framework.FilterSet):
    name_contains = django_filters.CharFilter(name="name", lookup_expr='icontains')
    name_abbreviation_contains = django_filters.CharFilter(name="slug", lookup_expr='icontains')
    citation = django_filters.CharFilter(name="citation", lookup_expr='icontains')
    court_name_contains = django_filters.CharFilter(name="court__name", lookup_expr='icontains')
    min_year = django_filters.NumberFilter(name="decisiondate", lookup_expr='gte')
    max_year = django_filters.NumberFilter(name="decisiondate", lookup_expr='lte')
    reporter_name_contains = django_filters.CharFilter(name="reporter__name", lookup_expr='iexact')
    jurisdiction = django_filters.ModelChoiceFilter(
        name='jurisdiction', lookup_expr='isnull',
        queryset=Jurisdiction.objects.all().order_by('name'),
    )
    class Meta:
        model = Case
        fields = ['name_contains', 'name_abbreviation_contains',
        'citation', 'jurisdiction', 'court_name_contains', 
        'min_year', 'max_year', 'reporter_name_contains']
