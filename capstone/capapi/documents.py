from django_elasticsearch_dsl import DocType, Index, fields
from capdb.models import CaseMetadata, CaseXML, VolumeMetadata, Jurisdiction, Court, Reporter

case = Index('cases')

case.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@case.doc_type
class CaseDocument(DocType):
    volume = fields.ObjectField(properties={
        "barcode": fields.TextField(),
        'volume_number': fields.KeywordField(),
    })

    reporter = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "full_name": fields.TextField()
    })

    court = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.TextField(),
        "name_abbreviation": fields.KeywordField()
    })
    jurisdiction = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.KeywordField(),
        "name_long": fields.KeywordField(),
        "whitelisted": fields.BooleanField()
    })

    judges = fields.StringField(analyzer='keyword', multi=True)
    parties = fields.StringField(analyzer='keyword', multi=True)
    attorneys = fields.StringField(analyzer='keyword', multi=True)
    docket_numbers = fields.ObjectField()
    opinions = fields.ObjectField()

    def prepare_docket_numbers(self, instance):
        if instance.docket_numbers:
            return instance.docket_numbers
        return { 'docket_numbers': None }

    def prepare_opinions(self, instance):
        if instance.opinions:
            return instance.opinions
        return { 'opinions': None }



    class Meta:
        model = CaseMetadata
        fields = [
            'name',
            'name_abbreviation',
            'last_page',
            'jurisdiction_name',
            'jurisdiction_name_long',
            'jurisdiction_slug',
            'jurisdiction_whitelisted',
            'decision_date',
            'district_name',
            'district_abbreviation',
            'duplicative',
            'case_id',
            'date_added',
        ]

    #def get_queryset(self):
    #    """Not mandatory but to improve performance we can select related in one sql request"""
    #    return super(CarDocument, self).get_queryset().select_related(
    #        'manufacturer'
    #    )

