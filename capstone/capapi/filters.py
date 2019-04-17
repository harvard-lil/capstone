from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils.functional import SimpleLazyObject
#from django.contrib.postgres.search import SearchQuery
from scripts.fts_temp import SearchQueryTemp

import rest_framework_filters as filters
from rest_framework.exceptions import ValidationError

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
reporter_choices = lazy_choices(models.Reporter.objects.all(), 'id', 'full_name')
jurisdiction_slug_to_id = SimpleLazyObject(lambda: dict(models.Jurisdiction.objects.values_list('slug', 'pk')))

class NoopMixin():
    """
        Mixin to allow method='noop' in filters.
    """
    def noop(self, qs, name, value):
        return qs

class MinLengthCharFilter(filters.CharFilter):
    def __init__(self, *args, **kwargs):
        self.min_length = kwargs.pop('min_length', 0)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value and len(value) < self.min_length:
            raise ValidationError({self.field_name: "Minimum query length is %s characters." % self.min_length})
        return super().filter(qs, value)

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


class CaseFilter(NoopMixin, filters.FilterSet):
    name_abbreviation = MinLengthCharFilter(
        field_name='name_abbreviation',
        label='Name Abbreviation (contains)',
        lookup_expr='icontains',
        min_length=3)
    cite = filters.CharFilter(
        field_name='cite',
        label='Citation',
        method='find_by_citation')
    court = filters.ChoiceFilter(
        field_name='court_slug',
        label='Court Slug',
        choices=court_choices)
    court_id = filters.NumberFilter(
        field_name='court_id',
        label='Court ID',
    )
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
    docket_number = MinLengthCharFilter(
        field_name='docket_number',
        label='Docket Number (contains)',
        lookup_expr='icontains',
        min_length=3)

    if settings.FULL_TEXT_FEATURE:
        search = filters.CharFilter(
            label='Full-Text Search',
            help_text='Search for words separated by spaces. All words are required in results. Words less than 3 characters are ignored.',
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
        choices=(('text', 'text only (default)'), ('html', 'HTML'), ('xml', 'XML'), ('tokens', 'debug tokens')),
    )

    def find_by_citation(self, qs, name, value):
        return qs.filter(citations__normalized_cite__exact=models.Citation.normalize_cite(value))

    def find_by_date(self, qs, name, value):
        try:
            if '_min' in name:
                return qs.filter(decision_date__gte=value)
            else:
                return qs.filter(decision_date__lte=value)
        except DjangoValidationError:
            raise ValidationError({name: "Invalid date format. Expected YYYY-MM-DD format."})

    def full_text_search_simple(self, qs, name, value):
        value = value.strip()
        value = " ".join(part for part in value.split() if len(part) > 2)
        if value:
            return qs.filter(
                case_text__tsv= parse_phrase_search(value)
            ).exclude(
                case_text=None  # ensure inner join
            ).extra(
                # For full-text search to be indexed properly, using the rum index, we have to order by the rum
                # operator that compares metadata_id to 0. Name the result 'fts_order' so we can order by it later.
                # See https://github.com/postgrespro/rum/issues/15#issuecomment-349690826
                select={'fts_order': 'capdb_casetext.metadata_id <=> 0'}
            ).order_by('fts_order')
        else:
            return qs

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
    jurisdiction = filters.MultipleChoiceFilter(
        choices=SimpleLazyObject(lambda: [['total', 'Total across jurisdictions (default)'], ['all', 'Select all jurisdictions']] + list(jur_choices)),
        method='jurisdiction_filter',
    )
    year = filters.CharFilter(
        method='year_filter',
        help_text='Use "total" to only show total value for all jurisdictions rather than per year',
    )
    q = filters.CharFilter(
        label='Words',
        help_text='Up to three words separated by spaces',
        method='q_filter',
    )

    class Meta:
        model = models.Ngram
        fields = ['jurisdiction', 'year', 'q']

    def q_filter(self, qs, name, value):
        return qs.from_string(value.strip().lower())

    def jurisdiction_filter(self, qs, name, value):
        """
            Handle list of jurisdictions.
        """
        if 'total' not in value and 'all' not in value:
            jurisdiction_ids = [jurisdiction_slug_to_id[slug] for slug in value]
            qs = qs.filter(observations__jurisdiction_id__in=jurisdiction_ids)
        return qs

    def year_filter(self, qs, name, value):
        if value != 'total':
            return qs.filter(observations__year=value)
        return qs


class NgramObservationFilter(filters.FilterSet):
    jurisdiction = filters.MultipleChoiceFilter(
        choices=SimpleLazyObject(lambda: [['total', 'Total across jurisdictions (default)'], ['all', 'Select all jurisdictions']] + list(jur_choices)),
        method='jurisdiction_filter',
    )
    year = filters.CharFilter(
        method='year_filter',
        help_text='Use "total" to only show total value for all jurisdictions rather than per year',
    )

    def __init__(self, data, *args, **kwargs):
        # default jurisdiction to 'total' so we don't load data for all jurisdictions unless requested
        if not data.get('jurisdiction'):
            data = data.copy()
            data['jurisdiction'] = 'total'
        super().__init__(data, *args, **kwargs)

    class Meta:
        model = models.NgramObservation
        fields = ['jurisdiction', 'year']

    def jurisdiction_filter(self, qs, name, value):
        """
            Handle list of jurisdictions.
        """
        # if 'all' provided, don't filter by jurisdiction
        if 'all' in value:
            return qs

        # If 'total' provided, include filter(jurisdiction=None) to get totals
        q = Q()
        if 'total' in value:
            q |= Q(jurisdiction_id=None)
            value.remove('total')

        # If others provided, include filter(jurisdiction_id__in=[]) to get those
        jurisdiction_ids = [jurisdiction_slug_to_id[slug] for slug in value]
        if jurisdiction_ids:
            q |= Q(jurisdiction_id__in=jurisdiction_ids)

        return qs.filter(q)

    def year_filter(self, qs, name, value):
        if value == 'total':
            value = None
        return qs.filter(year=value)



def parse_phrase_search(search_term):
    results = SearchQueryTemp("")
    normalized = search_term.replace('“', '"').replace('”', '"').replace('"', ' " ')

    # balance out uneven quotes by killing the last one
    if normalized.count('"') % 2 != 0:
        last_comma_index = normalized.rfind('"')
        normalized = "{} {}".format(normalized[:last_comma_index], normalized[last_comma_index + 1:])

    # I used this loop because my regex solution was harder to read, and just as much code
    current_phrase = []
    in_a_phrase = False
    for word in normalized.split(" "):
        if word == '':
            continue
        elif word == '"' and not in_a_phrase:
            in_a_phrase = True
        elif word == '"' and in_a_phrase:
            in_a_phrase = False
            results &= SearchQueryTemp(" ".join(current_phrase), search_type="phrase")
            current_phrase = []
        elif in_a_phrase:
            current_phrase.append(word)
        else:
            results &= SearchQueryTemp(word, search_type="plain")

    return results