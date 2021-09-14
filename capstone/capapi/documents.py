from difflib import SequenceMatcher
from itertools import groupby

from django_elasticsearch_dsl import Document, Index, fields
from django.conf import settings
from elasticsearch_dsl import Search, Q

from capdb.models import CaseMetadata, CaseLastUpdate
from scripts.helpers import alphanum_lower
from scripts.simhash import get_distance


def get_index(index_name):
    index = Index(settings.ELASTICSEARCH_INDEXES[index_name])
    index.settings(
        number_of_shards=1,
        number_of_replicas=0,
        max_result_window=settings.MAX_RESULT_WINDOW,
    )
    return index


indexes = {}
indexes['cases'] = cases_index = get_index("cases_endpoint")
indexes['resolve'] = resolve_index = get_index("resolve_endpoint")


def SuggestField(**kwargs):
    """
        Query 'foo' to get the TextField, or 'foo.raw' to get the KeywordField, or 'foo.suggest' to get the CompletionField.
    """
    return fields.TextField(
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        },
        **kwargs
    )


def FTSField(**kwargs):
    """
        index_phrases: optimize for "quoted searches"
        analyzer: tokenize based on English text
        index_options='offsets': allow for highlighting of long documents without increasing max_analyzed_offset
    """
    return fields.TextField(index_phrases=True, analyzer='english', index_options='offsets', **kwargs)


class DictField(fields.ObjectField):
    """
        Variant of ObjectField for indexing dictionaries of simple values. Just returns dictionary for serializing
        instead of calling serializers for subfields. This avoids errors if dict might be missing some fields.
    """
    def _get_inner_field_data(self, obj, field_value_to_ignore=None):
        if not obj:
            return {}
        if isinstance(obj, dict):
            return obj
        raise ValueError("DictField values must be dictionaries.""")


class RawSearch(Search):
    """
        Subclass of ElasticSearch DSL's Search object that returns raw dicts from ES, rather than wrapping in an object.
    """
    def _get_result(self, hit):
        return hit

    def execute(self, ignore_cache=False):
        self._response_class = lambda self, obj: obj
        return super().execute(ignore_cache)


@cases_index.doc_type
class CaseDocument(Document):
    # IMPORTANT: If you change what values are indexed here, also change the "CaseLastUpdate triggers"
    # section in set_up_postgres.py to keep Elasticsearch updated.
    name_abbreviation = SuggestField(analyzer='english')
    name = fields.TextField(index_phrases=True, analyzer='english')
    frontend_url = fields.KeywordField()
    frontend_pdf_url = fields.KeywordField()
    last_page = fields.KeywordField()
    first_page = fields.KeywordField()
    decision_date_original = fields.KeywordField()
    docket_numbers = fields.TextField(multi=True)
    docket_number = fields.TextField()
    last_updated = fields.KeywordField()
    #whitelisted =  fields.BooleanField()

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
        "rdb_normalized_cite": fields.KeywordField(),
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
            'opinions': fields.NestedField(multi=True, properties={
                'author': FTSField(),
                'text': FTSField(),
                'type': fields.KeywordField(),
                'extracted_citations': fields.NestedField(properties={
                    "cite": fields.KeywordField(),
                    "normalized_cite": fields.KeywordField(),
                    "rdb_normalized_cite": fields.KeywordField(),
                    "reporter": fields.KeywordField(),
                    "category": fields.KeywordField(),
                    "target_cases": fields.KeywordField(multi=True),
                    "groups": fields.ObjectField(),
                    "metadata": fields.ObjectField(),
                    "pin_cites": DictField(properties={
                        "page": fields.KeywordField(),
                        "parenthetical": FTSField(),
                    }),
                    "weight": fields.IntegerField(),
                    "year": fields.IntegerField(),
                    "opinion_id": fields.IntegerField(),
                })  
            }),
            'corrections': fields.TextField(),
        }),
    })

    analysis = fields.ObjectField(properties={
        'sha256': fields.KeywordField(),
        'simhash': fields.KeywordField(),
        'random_id': fields.DoubleField(),
        'random_bucket': fields.IntegerField(),
    })

    provenance = fields.ObjectField(properties={
        "date_added": fields.KeywordField(),
        "source": fields.KeywordField(),
        "batch": fields.KeywordField(),
    })

    restricted = fields.BooleanField()

    def prepare_provenance(self, instance):
        return {
            "date_added": instance.date_added.strftime('%Y-%m-%d'),
            "source": instance.source,
            "batch": instance.batch,
        }

    def prepare_frontend_pdf_url(self, instance):
        return instance.get_pdf_url(with_host=False)

    def prepare_analysis(self, instance):
        return {
            **dict(sorted((a.key, a.value) for a in instance.analysis.all())),
            'random_id': instance.random_id,
            'random_bucket': instance.random_id & 0xFFFF,
        }

    def prepare_docket_numbers(self, instance):
        if not hasattr(instance, 'docket_numbers'):
            return {'docket_numbers': None}
        return instance.docket_numbers

    def prepare_last_updated(self, instance):
        try:
            return instance.last_update.timestamp
        except CaseLastUpdate.DoesNotExist:
            return None

    def prepare_casebody_data(self, instance):
        body = instance.body_cache
        serializer = self._fields['casebody_data']['text']['opinions']['extracted_citations']
        # We must unroll to dict to support the `in` operator

        outbound_cites = instance.extracted_citations.all()
        cites_by_id = {k: list(v) for k,v in groupby(sorted(outbound_cites, key=lambda c: c.opinion_id), lambda c: c.opinion_id)}

        for i, opinion in enumerate(body.json['opinions']):
            if i in cites_by_id:
                body.json['opinions'][i]['extracted_citations'] = [serializer.get_value_from_instance(c) for c in cites_by_id[i]]

        return instance.redact_obj({
            'xml': body.xml,
            'html': body.html,
            'text': body.json,
        })

    def prepare_name(self, instance):
        return instance.redact_obj(instance.name)

    def prepare_name_abbreviation(self, instance):
        return instance.redact_obj(instance.name_abbreviation)

    class Django:
        model = CaseMetadata
        fields = [
            'id',
            'decision_date',
        ]
        ignore_signals = True
        auto_refresh = False

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
        return "%s, %s%s" % (
            self.name_abbreviation,
            ", ".join(cite.cite for cite in self.citations if cite.type != "vendor"),
            " (%s)" % (self.decision_date_original[:4],) if self.decision_date_original else ""
        )

    @classmethod
    def raw_search(cls, *args, **kwargs):
        """
            Return RawSearch object instead of Search object.
        """
        out = super().search(*args, **kwargs)
        out.__class__ = RawSearch
        return out


@resolve_index.doc_type
class ResolveDocument(Document):
    id = fields.KeywordField()
    source = fields.KeywordField()
    source_id = fields.KeywordField(attr='id')
    citations = fields.ObjectField(properties={
        "cite": fields.KeywordField(),
        "normalized_cite": fields.KeywordField(),
        "type": fields.KeywordField(),
        "volume": fields.KeywordField(),
        "reporter": fields.KeywordField(),
        "page": fields.KeywordField(),
        "page_int": fields.IntegerField(),
    })
    name_short = fields.TextField(attr='name_abbreviation')
    name_full = fields.TextField(attr='name')
    decision_date = fields.KeywordField(attr='decision_date_original')
    frontend_url = fields.KeywordField()
    api_url = fields.KeywordField()
    simhash = fields.KeywordField()

    class Django:
        model = CaseMetadata
        ignore_signals = True
        auto_refresh = False

    def prepare_id(self, instance):
        return 'cap-%s' % instance.id

    def prepare_source(self, instance):
        return 'cap'

    def prepare_simhash(self, instance):
        sh = next((i for i in instance.analysis.all() if i.key == 'simhash'), None)
        if sh:
            return sh.value

    def prepare_frontend_url(self, instance):
        return settings.RESOLVE_FRONTEND_PREFIX + instance.frontend_url

    def prepare_api_url(self, instance):
        return settings.RESOLVE_API_PREFIX + str(instance.id)

    def prepare_citations(self, instance):
        citations = []
        for cite in instance.citations.all():
            vol_num, reporter, page_num = cite.parsed()
            try:
                page_int = int(page_num)
            except (TypeError, ValueError):
                page_int = None
            citations.append({
                'cite': cite.cite,
                'normalized_cite': cite.normalized_cite,
                'type': cite.type,
                'volume': vol_num,
                'reporter': reporter,
                'page': page_num,
                'page_int': page_int,
            })
        return citations

    def prepare(self, instance):
        if type(instance) is dict:
            return instance
        return super().prepare(instance)

    def generate_id(self, object_instance):
        if type(object_instance) is dict:
            return object_instance['id']
        return object_instance.pk

    def full_cite(self):
        return "%s, %s%s" % (
            self.name_short,
            ", ".join(cite.cite for cite in self.citations if cite.type != "vendor"),
            " (%s)" % (self.decision_date[:4],) if self.decision_date else ""
        )

    def get_similar(self):
        candidates = ResolveDocument.search().query(
            'bool',
            should=[Q("match", citations__normalized_cite=c.normalized_cite) for c in self.citations]
        ).exclude("match", source=self.source).execute()

        # estimate similarities for each case
        for candidate in candidates:
            n1 = alphanum_lower(self.name_short)
            n2 = alphanum_lower(candidate.name_short)
            if n1 in n2 or n2 in n1:
                candidate.similarity = 1
            else:
                distances = [SequenceMatcher(None, n1, n2).ratio()]
                if self.simhash and candidate.simhash:
                    distances.append(get_distance(self.simhash, candidate.simhash))
                candidate.similarity = sum(distances)/len(distances)

        return candidates
