from functools import lru_cache

from django.utils.functional import SimpleLazyObject

import rest_framework_filters as filters

from capdb import models


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
        field_name='reporter__jurisdictions__slug',
        choices=jur_choices)

    reporter = filters.MultipleChoiceFilter(
        field_name='reporter__short_name',
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


