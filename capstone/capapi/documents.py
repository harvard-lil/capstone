from django_elasticsearch_dsl import Document as DocType, Index, fields
from django.conf import settings
from elasticsearch_dsl import Search

from capapi.resources import apply_replacements
from capdb.models import CaseMetadata

index = settings.ELASTICSEARCH_INDEXES['cases_endpoint']

case = Index(index)

case.settings(
    number_of_shards=1,
    number_of_replicas=0
)

def SuggestField():
    """
        Query 'foo' to get the TextField, or 'foo.raw' to get the KeywordField, or 'foo.suggest' to get the CompletionField.
    """
    return fields.TextField(
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        }
    )


class RawSearch(Search):
    """
        Subclass of ElasticSearch DSL's Search object that returns raw dicts from ES, rather than wrapping in an object.
    """
    def _get_result(self, hit):
        return hit

    def execute(self, ignore_cache=False):
        self._response_class = lambda self, obj: obj
        return super().execute(ignore_cache)


@case.doc_type
class CaseDocument(DocType):
    name_abbreviation = SuggestField()

    name = fields.TextField(index_phrases=True)

    frontend_url = fields.KeywordField()
    last_page = fields.KeywordField()
    first_page = fields.KeywordField()
    no_index = fields.KeywordField()
    duplicative = fields.KeywordField()
    no_index_notes = fields.KeywordField()

    docket_numbers = fields.TextField(multi=True)

    docket_number = fields.TextField()

    volume = fields.ObjectField(properties={
        "barcode": fields.KeywordField(),
        'volume_number': SuggestField(),
        'volume_number_slug': fields.KeywordField(),
    })

    reporter = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "full_name": SuggestField(),
        "short_name": SuggestField(),
        "short_name_slug": SuggestField(),
        "start_year": fields.KeywordField(),
        "end_year": fields.KeywordField(),
    })

    court = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.TextField(),
        "name_abbreviation": SuggestField(),
    })

    citations = fields.ObjectField(properties={
        "type": fields.TextField(),
        "cite": SuggestField(),
        "normalized_cite": fields.KeywordField(),
    })

    jurisdiction = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.KeywordField(),
        "name_long": SuggestField(),
        "whitelisted": fields.BooleanField()
    })

    casebody_data = fields.ObjectField(properties={
        'xml': fields.TextField(index=False),
        'html': fields.TextField(index=False),
        'text': fields.ObjectField(properties={
            'attorneys': fields.TextField(multi=True),
            'judges': fields.TextField(multi=True),
            'parties': fields.TextField(multi=True),
            'head_matter': fields.TextField(index_phrases=True),
            'opinions': fields.ObjectField(multi=True, properties={
                'author': fields.KeywordField(),
                'text': fields.TextField(index_phrases=True),
                'type': fields.KeywordField(),
            }),
            'corrections': fields.TextField(),
        }),
    })

    def prepare_docket_numbers(self, instance):
        if not hasattr(instance, 'docket_numbers'):
            return { 'docket_numbers': None }
        return instance.docket_numbers

    def prepare_casebody_data(self, instance):
        body = instance.body_cache
        return apply_replacements({
            'xml': body.xml,
            'html': body.html,
            'text': body.json,
        }, instance.no_index_redacted)

    def prepare_name(self, instance):
        return apply_replacements(instance.name, instance.no_index_redacted)

    def prepare_name_abbreviation(self, instance):
        return apply_replacements(instance.name_abbreviation, instance.no_index_redacted)

    class Django:
        model = CaseMetadata
        fields = [
            'id',
            'decision_date',
            'decision_date_original',
            'date_added',
        ]
        ignore_signals = True
        auto_refresh = False

    class Index:
        name = index

    def to_dict(self, skip_empty=False):
        # we need to do this until elasticsearch_dsl propagates skip_empty=False to the serialization that happens in
        # embedded objects.
        doc = super(CaseDocument, self).to_dict(skip_empty=skip_empty)
        doc['volume'] = self.volume.to_dict(skip_empty=skip_empty)
        doc['reporter'] = self.reporter.to_dict(skip_empty=skip_empty)
        doc['court'] = self.court.to_dict(skip_empty=skip_empty)
        doc['reporter'] = self.reporter.to_dict(skip_empty=skip_empty)
        doc['jurisdiction'] = self.jurisdiction.to_dict(skip_empty=skip_empty)
        doc['casebody_data']['text'] = self.casebody_data.text.to_dict(skip_empty=skip_empty)
        doc['casebody_data']['text']['opinions'] = [ op.to_dict(skip_empty=skip_empty) for op in self.casebody_data['text'].opinions ]
        return doc

    def full_cite(self):
        from capdb.models import Citation  # avoid circular import
        return "%s, %s%s" % (
            self.name_abbreviation,
            ", ".join(cite.cite for cite in Citation.sorted_by_type(self.citations) if cite.type != "vendor"),
            " (%s)" % self.decision_date.year if self.decision_date else ""
        )

    @classmethod
    def raw_search(cls, *args, **kwargs):
        """
            Return RawSearch object instead of Search object.
        """
        out = super().search(*args, **kwargs)
        out.__class__ = RawSearch
        return out