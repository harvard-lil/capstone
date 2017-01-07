import django_filters
from .models import Case
from .serializers import CaseSerializer
from rest_framework import generics

class CaseFilter(django_filters.rest_framework.FilterSet):
    jurisdiction = django_filters.CharFilter(name="jurisdiction__name", lookup_expr='iexact')
    court = django_filters.CharFilter(name="court__name", lookup_expr='icontains')
    name = django_filters.CharFilter(name="name", lookup_expr='icontains')
    citation = django_filters.CharFilter(name="citation", lookup_expr='icontains')
    min_year = django_filters.NumberFilter(name="decisiondate", lookup_expr='gte')
    max_year = django_filters.NumberFilter(name="decisiondate", lookup_expr='lte')
    reporter = django_filters.CharFilter(name="reporter__name", lookup_expr='iexact')
    slug = django_filters.CharFilter(name="slug", lookup_expr='icontains')

    class Meta:
        model = Case
        fields = ['jurisdiction', 'court', 'name', 'citation']
