import re

from django_elasticsearch_dsl import DocType, Index, fields
from capdb.models import CaseMetadata

from scripts.generate_case_html import generate_html
from scripts.helpers import ordered_query_iterator

case = Index('cases')

case.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@case.doc_type
class CaseDocument(DocType):
    name_abbreviation = fields.StringField(
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        }
    )

    name_abbreviation = fields.StringField(
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        }
    )

    name = fields.TextField()

    docket_numbers = fields.ObjectField()

    volume = fields.ObjectField(properties={
        "barcode": fields.TextField(),
        'volume_number': fields.StringField(
            fields={
                'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
            })
    })

    reporter = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "full_name": fields.StringField(
            fields={
                'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
            })
    })

    court = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.TextField(),
        "name_abbreviation": fields.StringField(
            fields={
                'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
            })
    })

    jurisdiction = fields.ObjectField(properties={
        "id": fields.IntegerField(),
        "slug": fields.KeywordField(),
        "name": fields.KeywordField(),
        "name_long": fields.StringField(
            fields={
                'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
            }),
        "whitelisted": fields.BooleanField()
    })

    casebody_data = fields.NestedField(properties={
        'text': fields.TextField(),
        'xml': fields.KeywordField(),
        'html': fields.KeywordField(),
        'structured': fields.NestedField(properties={
            'attorneys': fields.KeywordField(multi=True),
            'judges': fields.KeywordField(multi=True),
            'parties': fields.KeywordField(multi=True),
            'headmatter': fields.KeywordField(multi=True),
            'opinions': fields.ObjectField(),
        }),
    })


    def prepare_docket_numbers(self, instance):
        if not hasattr(instance, 'docket_numbers'):
            return { 'docket_numbers': None }
        return instance.docket_numbers

    def prepare_casebody_data(self, instance):
        if not hasattr(instance, 'case_xml'):
            return { 'case_body': {
                'data': None,
                'status': 'Casebody not found during indexing. Please send the CAP team this URL '
                          'and this error message.'
            }}


        parsed_casebody = instance.case_xml.extract_casebody()

        # For the plain text output, footnotes should keep their labels in the text, but we want to make sure
        # there is a space separating the labels from the first word. Otherwise a text analysis comes up with
        # a lot of noise like "1The".
        for footnote in parsed_casebody('casebody|footnote'):
            label = footnote.attrib.get('label')
            if label:
                # Get text of footnote and replace "[label][nonwhitespace char]" with "[label][nonwhitespace char]"
                footnote_paragraph = parsed_casebody(footnote[0])
                new_text = footnote_paragraph.text()
                new_text = re.sub(r'^(%s)(\S)' % re.escape(label), r'\1 \2', new_text)
                footnote_paragraph.text(new_text)

        # extract each opinion into a dictionary
        opinions = []
        for opinion in parsed_casebody.items('casebody|opinion'):
            opinions.append({
                'type': opinion.attr('type'),
                'author': opinion('casebody|author').text() or None,
                'text': opinion.text(),
            })

            # remove opinion so it doesn't get included in head_matter below
            opinion.remove()

        return {
            'data': {
                'text': instance.case_xml.extract_casebody().text(),
                'xml': instance.case_xml.orig_xml,
                'html': generate_html(parsed_casebody),
                'structured': {
                    'attorneys': instance.attorneys,
                    'judges': instance.judges,
                    'parties': instance.parties,
                    'headmatter': parsed_casebody.text(),
                    'opinions': opinions,
                }
            }
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

    def get_queryset(self):
        return ordered_query_iterator(
            super(CaseDocument, self).get_queryset()
            .select_related(
                'volume',
                'reporter',
                'court',
                'jurisdiction',
                'reporter',
                'case_xml')
            .in_scope()
            .order_by('decision_date', 'id')  # we have an index on this ordering with in_scope(), so ordered_query_iterator can run efficiently
        )

