import re
from difflib import SequenceMatcher

from django_elasticsearch_dsl import Document, Index, fields
from django.conf import settings
from elasticsearch_dsl import Search, Q

from capdb.models import CaseMetadata, CaseLastUpdate
from scripts.simhash import get_distance


## helpers

def get_index(index_key, fallback_index_key=None):
    index_name = settings.ELASTICSEARCH_INDEXES.get(index_key) or settings.ELASTICSEARCH_INDEXES[fallback_index_key]
    index = Index(index_name)
    index.settings(
        number_of_shards=1,
        number_of_replicas=0,
        max_result_window=settings.MAX_PAGE_SIZE+1,  # allow for one extra for pagination
    )
    return index


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


class WriteOnlyDocument():
    def search(*args, **kwargs):
        raise NotImplementedError("Use reader object")
    def get(*args, **kwargs):
        raise NotImplementedError("Use reader object")
    def mget(*args, **kwargs):
        raise NotImplementedError("Use reader object")


class ReadOnlyDocument(Document):
    def update(*args, **kwargs):
        raise NotImplementedError("Use writer object")


## base documents

class CaseDocument(Document):
    # IMPORTANT: If you change what values are indexed here, also change the "CaseLastUpdate triggers"
    # section in set_up_postgres.py to keep Elasticsearch updated.
    name_abbreviation = SuggestField()
    name = fields.TextField(index_phrases=True)
    frontend_url = fields.KeywordField()
    frontend_pdf_url = fields.KeywordField()
    last_page = fields.KeywordField()
    first_page = fields.KeywordField()
    decision_date_original = fields.KeywordField()
    docket_numbers = fields.TextField(multi=True)
    docket_number = fields.TextField()
    last_updated = fields.KeywordField()

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

    extractedcitations = fields.ObjectField(properties={
        "cite": fields.KeywordField(),
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

    analysis = fields.ObjectField(properties={
        'sha256': fields.KeywordField(),
        'simhash': fields.KeywordField(),
    })

    def prepare_frontend_pdf_url(self, instance):
        return instance.get_pdf_url(with_host=False)

    def prepare_analysis(self, instance):
        return dict(sorted((a.key, a.value) for a in instance.analysis.all()))

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
        doc['cites_to'] = self.extractedcitations
        return doc

    def full_cite(self):
        return "%s, %s%s" % (
            self.name_abbreviation,
            ", ".join(cite.cite for cite in self.citations if cite.type != "vendor"),
            " (%s)" % (self.decision_date_original[:4],) if self.decision_date_original else ""
        )


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


## readers and writers

# Sometimes we want to point search results at a copy of the index while we update the primary index,
# so our base documents are split into separate documents for reading and writing.


cases_writer_index = get_index("cases_endpoint")
resolve_writer_index = get_index("resolve_endpoint")
cases_reader_index = get_index("cases_reader_endpoint", "cases_endpoint")
resolve_reader_index = get_index("resolve_reader_endpoint", "resolve_endpoint")


@cases_writer_index.doc_type
class CaseWriterDocument(WriteOnlyDocument, CaseDocument):
    pass


@resolve_writer_index.doc_type
class ResolveWriterDocument(WriteOnlyDocument, ResolveDocument):
    pass


@cases_reader_index.doc_type
class CaseReaderDocument(ReadOnlyDocument, CaseDocument):

    @classmethod
    def raw_search(cls, *args, **kwargs):
        """
            Return RawSearch object instead of Search object.
        """
        out = super().search(*args, **kwargs)
        out.__class__ = RawSearch
        return out


@resolve_reader_index.doc_type
class ResolveReaderDocument(ReadOnlyDocument, ResolveDocument):

    def get_similar(self):
        candidates = type(self).search().query(
            'bool',
            should=[Q("match", citations__normalized_cite=c.normalized_cite) for c in self.citations]
        ).exclude("match", source=self.source).execute()

        # estimate similarities for each case
        for candidate in candidates:
            n1 = re.sub(r'[^a-z0-9]', '', self.name_short.lower())
            n2 = re.sub(r'[^a-z0-9]', '', candidate.name_short.lower())
            if n1 in n2 or n2 in n1:
                candidate.similarity = 1
            else:
                distances = [SequenceMatcher(None, n1, n2).ratio()]
                if self.simhash and candidate.simhash:
                    distances.append(get_distance(self.simhash, candidate.simhash))
                candidate.similarity = sum(distances)/len(distances)

        return candidates
