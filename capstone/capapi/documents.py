from django_elasticsearch_dsl import DocType, Index, fields
from capdb.models import CaseMetadata

case = Index('cases')

case.settings(
    number_of_shards=1,
    number_of_replicas=0
)

def SuggestField():
    return fields.StringField(
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        }
    )

@case.doc_type
class CaseDocument(DocType):
    name_abbreviation = SuggestField()

    name = fields.TextField()

    frontend_url = fields.KeywordField()

    docket_numbers = fields.KeywordField(multi=True)

    volume = fields.ObjectField(properties={
        "barcode": fields.TextField(),
        'volume_number': SuggestField(),
    })

    reporter = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "full_name": SuggestField(),
        "short_name": SuggestField(),
    })

    court = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.TextField(),
        "name_abbreviation": SuggestField(),
    })

    jurisdiction = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.KeywordField(),
        "name_long": SuggestField(),
        "whitelisted": fields.BooleanField()
    })

    casebody_data = fields.ObjectField(properties={
        'text': fields.TextField(),
        'xml': fields.TextField(index=False),
        'html': fields.TextField(index=False),
        'structured': fields.ObjectField(properties={
            'attorneys': fields.TextField(multi=True),
            'judges': fields.TextField(multi=True),
            'parties': fields.TextField(multi=True),
            'head_matter': fields.TextField(),
            'opinions': fields.NestedField(properties={
                'author': fields.KeywordField(),
                'text': fields.TextField(),
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
        return {
            'text': body.text,
            'xml': body.xml,
            'html': body.html,
            'structured': body.json,
        }

    class Meta:
        model = CaseMetadata
        fields = [
            'id',
            'last_page',
            'first_page',
            'decision_date',
            'duplicative',
            'date_added',
        ]
        ignore_signals = True
        auto_refresh = False