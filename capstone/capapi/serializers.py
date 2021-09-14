from collections import defaultdict
from functools import reduce

from django.db import transaction
from django_elasticsearch_dsl_drf.utils import DictionaryProxy
from rest_framework import serializers
from rest_framework.reverse import reverse as api_reverse
from rest_framework.serializers import ListSerializer
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer

from .models import SiteLimits
from .documents import CaseDocument, ResolveDocument
from capdb import models
from capweb.helpers import reverse
from user_data.models import UserHistory


class UserHistoryMixin:
    """
        Mixin because we have to apply this to the regular serializer and also the list serializer.
    """
    @property
    def data(self):
        """
            After serializing user history data, we have records like {'case_id': 123, 'date': <date>}.
            Extract all of the 'case_id' fields and use CaseDocument.mget to fetch the case metadata
            for each case.
        """
        result = super().data
        records = result if hasattr(self, 'many') else [result]
        if records:
            cases = CaseDocument.mget([r['case_id'] for r in records])
            cases_by_id = {c.id: c for c in cases}
            for r in records:
                case = cases_by_id.get(r['case_id'])
                if case:
                    r['case'] = CaseDocumentSerializer(case).data
                else:
                    r['case'] = None
        return result


class UserHistoryListSerializer(UserHistoryMixin, ListSerializer):
    pass


class UserHistorySerializer(UserHistoryMixin, serializers.ModelSerializer):
    class Meta:
        model = UserHistory
        fields = ('date', 'case_id')
        list_serializer_class = UserHistoryListSerializer


class CitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Citation
        fields = ('type', 'cite')


class CitationWithCaseSerializer(CitationSerializer):
    case_url = serializers.HyperlinkedRelatedField(source='case', view_name='cases-detail',
                                                   read_only=True, lookup_field='id')
    class Meta:
        model = models.Citation
        fields = CitationSerializer.Meta.fields + ('case_id', 'case_url')


class JurisdictionSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="jurisdiction-detail",
        lookup_field='slug')

    class Meta:
        model = models.Jurisdiction
        fields = ('url', 'id', 'slug', 'name', 'name_long', 'whitelisted')

# for elasticsearch
class BaseDocumentSerializer(DocumentSerializer):
    _abstract = True

    def __init__(self, *args, **kwargs):
        """
            If we are instantiated with an Elasticsearch wrapper object, convert to a bare dictionary.
        """
        super().__init__(*args, **kwargs)
        if isinstance(self.instance, CaseDocument):
            self.instance = self.instance._d_
        elif isinstance(self.instance, DictionaryProxy):
            self.instance = self.instance.to_dict()

    def s_from_instance(self, instance):
        if "_source" in instance:
            return instance["_source"]
        elif type(instance) is CaseDocument:
            return instance._d_
        else:
            return instance


class CaseDocumentSerializer(BaseDocumentSerializer):

    class Meta:
        document = CaseDocument

    _url_templates = None

    def deep_get(self, dictionary, keys, default=[]):
        """ https://stackoverflow.com/questions/25833613/safe-method-to-get-value-of-nested-dictionary """
        return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys, dictionary)

    def get_preview(self, instance):
        preview_source, preview_inner = [], []
        if "_source" in instance:
            preview_source = [highlight for highlights in instance['highlight'].values() for highlight in highlights] if 'highlight' in instance else []
        if 'inner_hits' in instance:
            for nested_field, nested_hits in instance['inner_hits'].items():
                access_array = ['hits', 'hits']
                _ = [preview_inner.extend(list(highlight['highlight'].values()))
                        for highlight in self.deep_get(nested_hits,access_array)
                        if 'highlight' in highlight]
                preview_inner = [item for sublist in preview_inner for item in sublist]

        return preview_source + preview_inner

    def to_representation(self, instance):
        """
            Convert ES result to output dictionary for the API.
        """
        # cache url templates to avoid lookups for each object serialized
        if not self._url_templates:
            def placeholder_url(name):
                return api_reverse(name, ['REPLACE']).replace('REPLACE', '%s')
            cite_home = reverse('cite_home', host='cite').rstrip('/')
            CaseDocumentSerializer._url_templates = {
                'case_url': placeholder_url("cases-detail"),
                'frontend_url': cite_home + '%s',
                'frontend_pdf_url': cite_home + '%s',
                'volume_url': placeholder_url("volumemetadata-detail"),
                'reporter_url': placeholder_url("reporter-detail"),
                'court_url': placeholder_url("court-detail"),
                'jurisdiction_url': placeholder_url("jurisdiction-detail"),
            }

        def as_dict(obj):
            if type(obj) == dict:
                return obj
            return obj._d_

        s = self.s_from_instance(instance)

        # get extracted_citations list, removing duplicate c["cite"] values
        extracted_citations = []
        ec = [o['extracted_citations'] for o in s['casebody_data']['text']['opinions'] if 'extracted_citations' in o]
        ec = [item for sublist in ec for item in sublist]
        for c in ec:
            c = as_dict(c)
            extracted_cite = {
                "cite": c["cite"],
                "category": c.get('category'),
                "reporter": c.get('reporter'),
            }
            if c.get("target_cases"):
                extracted_cite["case_ids"] = c["target_cases"]
            if int(c.get('weight', 1)) > 1:
                extracted_cite['weight'] = int(c['weight'])
            if c.get('year'):
                extracted_cite['year'] = c['year']
            if c.get('pin_cites'):
                extracted_cite['pin_cites'] = c['pin_cites']
            if isinstance(c.get('opinion_id'), int):
                extracted_cite['opinion_id'] = c['opinion_id'] - 1
            extracted_citations.append(extracted_cite)

        # move head_matter outside of casebody_data
        head_matter = list(filter(lambda x: x['type'] == 'head_matter', s['casebody_data']['text']['opinions']))
        head_matter = head_matter[0] if head_matter else []
        if head_matter:
            s['casebody_data']['text']['opinions'].remove(head_matter)

        if 'text' in head_matter:
            s['casebody_data']['text']['head_matter'] = head_matter['text']

        # strip citations from casebody data
        for i, element in enumerate(s['casebody_data']['text']['opinions']):
            if 'extracted_citations' in element:
                del s['casebody_data']['text']['opinions'][i]['extracted_citations']

        preview = self.get_preview(instance)

        # IMPORTANT: If you change what values are exposed here, also change the "CaseLastUpdate triggers"
        # section in set_up_postgres.py to keep Elasticsearch updated.
        return {
            "id": s["id"],
            "url": self._url_templates['case_url'] % s["id"],
            "name": s["name"],
            "name_abbreviation": s["name_abbreviation"],
            "decision_date": s["decision_date_original"],
            "docket_number": s["docket_number"],
            "first_page": s["first_page"],
            "last_page": s["last_page"],
            "citations": [{"type": c["type"], "cite": c["cite"]} for c in s["citations"]],
            "volume": {
                "url": self._url_templates['volume_url'] % s["volume"]["barcode"],
                "volume_number": s["volume"]["volume_number"],
                "barcode": s["volume"]["barcode"],
            },
            "reporter": {
                "url": self._url_templates['reporter_url'] % s["reporter"]["id"],
                "full_name": s["reporter"]["full_name"],
                "id": s["reporter"]["id"]
            },
            "court": {
                "url": self._url_templates['court_url'] % s["court"]['slug'],
                "name_abbreviation": s["court"]["name_abbreviation"],
                "slug": s["court"]["slug"],
                "id": s["court"]["id"],
                "name": s["court"]["name"],
            },
            "jurisdiction": {
                "id": s["jurisdiction"]["id"],
                "name_long": s["jurisdiction"]["name_long"],
                "url": self._url_templates['jurisdiction_url'] % s["jurisdiction"]["slug"],
                "slug": s["jurisdiction"]["slug"],
                "whitelisted": s["jurisdiction"]["whitelisted"],
                "name": s["jurisdiction"]["name"],
            },
            "cites_to": extracted_citations,
            "frontend_url": self._url_templates['frontend_url'] % s["frontend_url"],
            "frontend_pdf_url": self._url_templates['frontend_pdf_url'] % s["frontend_pdf_url"] if s["frontend_pdf_url"] else None,
            "preview": preview,
            "analysis": s.get("analysis", {}),
            "last_updated": s["last_updated"] or s["provenance"]["date_added"],
            "provenance": s["provenance"],
        }


class ResolveDocumentListSerializer(ListSerializer):
    def to_representation(self, data):
        extracted_cites = self.context['request'].extracted_cites
        out = defaultdict(list)
        for hit in data.execute()['hits']['hits']:
            case = hit['_source']
            case.pop('id')
            for cite in case['citations']:
                cite.pop('page_int', None)
                if cite['normalized_cite'] in extracted_cites:
                    out[extracted_cites[cite['normalized_cite']]].append(case)
        return out

    @property
    def data(self):
        return super(ListSerializer, self).data


class ResolveDocumentSerializer(BaseDocumentSerializer):
    class Meta:
        document = ResolveDocument
        list_serializer_class = ResolveDocumentListSerializer


class CaseAllowanceMixin:
    """
        When we serialize case bodies for delivery to the client, we need to make sure, in a race-condition-free
        way, that the correct case allowance is checked and updated. That's handled here by overriding
        serializer.data.

        Do this as a mixin because we have to apply it to the regular serializer and also the list serializer.
    """
    @property
    def data(self):
        request = self.context.get('request')
        user = request.user

        if user.is_anonymous:
            # logged out users won't get any restricted case bodies, so nothing to update
            return super().data

        # set request.site_limits so it can be checked later in check_update_case_permissions()
        request.site_limits = SiteLimits.get()

        with transaction.atomic(), transaction.atomic(using='user_data'):
            # for logged-in users, fetch the current user data here inside a transaction, using select_for_update
            # to lock the row so we don't collide with any simultaneous requests
            refreshed_user = user.__class__.objects.select_for_update().get(pk=user.pk)

            # update the info for the existing user model, in case it's changed since the request began
            if not user.unlimited_access_in_effect():
                user.case_allowance_remaining = refreshed_user.case_allowance_remaining
                user.case_allowance_last_updated = refreshed_user.case_allowance_last_updated
                user.has_tracked_history = refreshed_user.has_tracked_history
                user.update_case_allowance(save=False)  # for SiteLimits, make sure we start with up-to-date case_allowance_remaining
                allowance_before = user.case_allowance_remaining

            # pre-fetch IDs of any restricted cases in our results that this user has already accessed
            if user.has_tracked_history:
                if hasattr(self, 'many'):
                    case_ids = [case["_source"]['id'] for case in self.instance if case["_source"]["restricted"]]
                else:
                    case_ids = [self.instance['id']]
                allowed_case_ids = set(UserHistory.objects.filter(case_id__in=case_ids, user_id=user.id).values_list('case_id', flat=True).distinct())
                self.context['allowed_case_ids'] = allowed_case_ids

            result = super().data

            # store history
            if user.track_history:
                cases = result if hasattr(self, 'many') else [result]  # self.many means this is a list view
                to_create = [UserHistory(user_id=user.id, case_id=c['id']) for c in cases if c['casebody']['status'] == 'ok']
                if to_create:
                    UserHistory.objects.bulk_create(to_create)
                    user.has_tracked_history = True

            # if user's case allowance was updated, save
            # (this works because it's part of the same transaction with the select_for_update --
            # we don't have to use the same object)
            if user.tracker.changed():
                user.save()

        # update site-wide limits
        if not user.unlimited_access_in_effect():
            cases_sent = allowance_before - user.case_allowance_remaining
            SiteLimits.add_values(daily_downloads=cases_sent)

        return result


class ListSerializerWithCaseAllowance(CaseAllowanceMixin, ListSerializer):
    """ Custom ListSerializer for CaseDocumentSerializerWithCasebody that enforces CaseAllowance. """
    pass


class CaseDocumentSerializerWithCasebody(CaseAllowanceMixin, CaseDocumentSerializer):
    class Meta:
        document = CaseDocument
        list_serializer_class = ListSerializerWithCaseAllowance

    def to_representation(self, instance, check_permissions=True):
        case = super().to_representation(instance)
        request = self.context.get('request')
        s = self.s_from_instance(instance)

        # check permissions for full-text access to this case
        if not check_permissions:
            status = 'ok'
        elif s['restricted'] is False:
            status = "ok"
        elif request.user.is_anonymous:
            status = "error_auth_required"
        elif request.user.has_tracked_history and case['id'] in self.context['allowed_case_ids']:
            status = "ok"
        elif request.site_limits.daily_downloads >= request.site_limits.daily_download_limit:
            status = "error_sitewide_limit_exceeded"
        else:
            try:
                request.user.update_case_allowance(case_count=1, save=False)
                status = "ok"
            except AttributeError:
                status = "error_limit_exceeded"

        # render case
        data = None
        if status == 'ok':
            body_format = self.context.get('force_body_format') or request.query_params.get('body_format')
            if body_format not in ('html', 'xml'):
                body_format = 'text'
            data = s['casebody_data'][body_format]

        case['casebody'] = {'status': status, 'data': data}
        return case


class VolumeSerializer(serializers.ModelSerializer):
    jurisdictions = JurisdictionSerializer(source='reporter.jurisdictions', many=True)
    reporter_url = serializers.HyperlinkedRelatedField(source='reporter', view_name='reporter-detail', read_only=True)
    reporter = serializers.ReadOnlyField(source='xml_reporter_full_name')
    start_year = serializers.ReadOnlyField(source='xml_start_year')
    end_year = serializers.ReadOnlyField(source='xml_end_year')
    publisher = serializers.ReadOnlyField(source='xml_publisher')
    pdf_url = serializers.FileField(source='pdf_file')
    frontend_url = serializers.ReadOnlyField(source='get_frontend_url')

    class Meta:
        model = models.VolumeMetadata
        fields = (
            'url',
            'barcode',
            'volume_number',
            'title',
            'publisher',
            'publication_year',
            'start_year',
            'end_year',
            'nominative_volume_number',
            'nominative_name',
            'series_volume_number',
            'reporter',
            'reporter_url',
            'jurisdictions',
            'pdf_url',
            'frontend_url',
        )


class ReporterSerializer(serializers.ModelSerializer):
    jurisdictions = JurisdictionSerializer(many=True)
    frontend_url = serializers.ReadOnlyField(source='get_frontend_url')

    class Meta:
        model = models.Reporter
        fields = (
            'id',
            'url',
            'full_name',
            'short_name',
            'start_year',
            'end_year',
            'jurisdictions',
            'frontend_url',
        )


class CourtSerializer(serializers.ModelSerializer):
    jurisdiction_url = serializers.HyperlinkedRelatedField(
        source='jurisdiction', view_name='jurisdiction-detail', read_only=True, lookup_field='slug')
    jurisdiction = serializers.ReadOnlyField(source='jurisdiction.name')
    url = serializers.HyperlinkedIdentityField(
        view_name="court-detail",
        lookup_field='slug')

    class Meta:
        model = models.Court
        fields = (
            'id',
            'url',
            'name',
            'name_abbreviation',
            'jurisdiction',
            'jurisdiction_url',
            'slug',
        )


### BULK SERIALIZERS ###

class CaseExportSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = models.CaseExport
        fields = ('id', 'download_url', 'file_name', 'export_date', 'public', 'filter_type', 'filter_id', 'body_format')

    def get_download_url(self, obj):
        return api_reverse('caseexport-download', kwargs={'pk': obj.pk}, request=self.context.get('request'))


class NoLoginCaseDocumentSerializer(CaseDocumentSerializerWithCasebody):
    def to_representation(self, instance, check_permissions=False):
        """ Tell get_casebody not to check for case download permissions. """
        return super().to_representation(instance, check_permissions=check_permissions)

    @property
    def data(self):
        """ Skip tracking of download counts. """
        return super(DocumentSerializer, self).data
