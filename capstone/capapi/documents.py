import re

from django_elasticsearch_dsl import DocType, Index, fields
from django.conf import settings
from django.utils.text import slugify

from capdb.models import CaseMetadata
from capweb.helpers import reverse

index = settings.ELASTICSEARCH_INDEXES['cases_endpoint']

case = Index(index)

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
        return {
            'xml': body.xml,
            'html': body.html,
            'text': body.json,
        }

    class Meta:
        model = CaseMetadata
        fields = [
            'id',
            'decision_date',
            'date_added',
        ]
        ignore_signals = True
        auto_refresh = False

    def full_cite(self):
        return "%s, %s%s" % (
            self.name_abbreviation,
            ", ".join(cite.cite for cite in self.citations),
            " (%s)" % self.decision_date.year if self.decision_date else ""
        )

    def get_frontend_url(self, disambiguate=False, include_host=True):

        """
            Return cite.case.law cite for this case, like /series/volnum/pagenum/.
            If disambiguate is true, return /series/volnum/pagenum/id/.
        """
        cite = self.citations[0].cite
        # try to match "(volnumber) (series) (pagenumber)"
        m = re.match(r'(\S+)\s+(.+?)\s+(\S+)$', cite)
        if not m:
            # if cite doesn't match the expected format, always disambiguate so URL resolution doesn't depend on cite value
            disambiguate = True
            # try to match "(year)-(series)-(case index)", e.g. "2017-Ohio-5699" and "2015-NMCA-053"
            m = re.match(r'(\S+)-(.+?)-(\S+)$', cite)

        cite_parts = m.groups() if m else [self.volume.volume_number, self.reporter.short_name, self.first_page]
        args = [slugify(cite_parts[1]), cite_parts[0], cite_parts[2]] + ([self.id] if disambiguate else [])
        url = reverse('citation', args=args, host='cite')
        if not include_host:
            # strip https://cite.case.law prefix so stored value can be moved between servers
            url = '/'+url.split('/',3)[3]
        return url