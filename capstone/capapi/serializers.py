import logging

from django.db import transaction
from rest_framework import serializers
from rest_framework.reverse import reverse as api_reverse
from rest_framework.serializers import ListSerializer

from capapi.models import SiteLimits
from capapi.renderers import HTMLRenderer, XMLRenderer
from capdb import models
from capdb.models import CaseBodyCache
from capweb.helpers import reverse
from scripts import helpers
from .permissions import check_update_case_permissions

logger = logging.getLogger(__name__)

from django_elasticsearch_dsl_drf.serializers import DocumentSerializer

from .documents import CaseDocument

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
class CaseDocumentSerializer(DocumentSerializer):
    url = serializers.SerializerMethodField()
    frontend_url = serializers.SerializerMethodField()
    reporter = serializers.SerializerMethodField()
    volume = serializers.SerializerMethodField()
    court = serializers.SerializerMethodField()
    jurisdiction = serializers.SerializerMethodField()
    citations = serializers.SerializerMethodField()

    class Meta:
        document = CaseDocument
        fields = (
            'id',
            'url',
            'name',
            'citations',
            'name_abbreviation',
            'decision_date',
            'docket_number',
            'first_page',
            'last_page',
            'citations',
            'volume',
            'reporter',
            'court',
            'jurisdiction',
            'frontend_url',
        )

    def get_reporter(self, obj):
        return_dict = {
            "full_name": obj.reporter['full_name'],
            "id": obj.reporter['id'],
            "url": api_reverse('reporter-detail', [obj.reporter['id']]),
        }
        return return_dict

    def get_citations(self, obj):
        return_list = [ { 'type': citation['type'], 'cite': citation['cite'] } for citation in obj.citations ]
        return return_list

    def get_volume(self, obj):

        volume_number = None
        if hasattr(obj.volume, 'volume_number'):
            volume_number = getattr(obj.volume, 'volume_number', None)
        elif hasattr(obj.volume, 'get'):
            volume_number = obj.volume.get('volume_number')

        return_dict = {
            "barcode": obj.volume['barcode'],
            "volume_number": volume_number,
            "url": api_reverse('volumemetadata-detail', [obj.volume['barcode']]),
        }
        return return_dict

    def get_court(self, obj):
        return_dict = {
            "id": obj.court['id'],
            "slug": obj.court['slug'],
            "name": obj.court['name'],
            "name_abbreviation": obj.court['name_abbreviation'],
            "url": api_reverse('court-detail', [obj.court['slug']]),

        }
        return return_dict

    def get_jurisdiction(self, obj):
        return_dict = {
            "id": obj.jurisdiction['id'],
            "slug": obj.jurisdiction['slug'],
            "name": obj.jurisdiction['name'],
            "name_long": obj.jurisdiction['name_long'],
            "whitelisted": obj.jurisdiction['whitelisted'],
            "url": api_reverse('jurisdiction-detail', [obj.jurisdiction['slug']]),
        }
        return return_dict

    def get_frontend_url(self, obj):
        if not hasattr(self, '_frontend_url_base'):
            CaseDocumentSerializer._frontend_url_base = reverse('cite_home', host='cite').rstrip('/')
        return self._frontend_url_base + (obj.frontend_url or '')

    def get_url(self, obj):
        return api_reverse('cases-detail', [obj.id])

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

        if request.user.is_anonymous:
            # logged out users won't get any blacklisted case bodies, so nothing to update
            return super().data

        # set request.site_limits so it can be checked later in check_update_case_permissions()
        request.site_limits = SiteLimits.get()

        with transaction.atomic():
            # for logged-in users, fetch the current user data here inside a transaction, using select_for_update
            # to lock the row so we don't collide with any simultaneous requests
            user = request.user.__class__.objects.select_for_update().get(pk=request.user.pk)

            # update the info for the existing user model, in case it's changed since the request began
            if not request.user.unlimited_access_in_effect():
                request.user.case_allowance_remaining = user.case_allowance_remaining
                request.user.case_allowance_last_updated = user.case_allowance_last_updated
                request.user.update_case_allowance(save=False)  # for SiteLimits, make sure we start with up-to-date case_allowance_remaining
                allowance_before = request.user.case_allowance_remaining

            result = super().data

            # if user's case allowance was updated, save
            # (this works because it's part of the same transaction with the select_for_update --
            # we don't have to use the same object)
            if request.user.tracker.changed():
                request.user.save()

        # update site-wide limits
        if not request.user.unlimited_access_in_effect():
            cases_sent = allowance_before - request.user.case_allowance_remaining
            SiteLimits.add_values(daily_downloads=cases_sent)

        return result


class ListSerializerWithCaseAllowance(CaseAllowanceMixin, ListSerializer):
    """ Custom ListSerializer for CaseDocumentSerializerWithCasebody that enforces CaseAllowance. """
    pass


class CaseDocumentSerializerWithCasebody(CaseAllowanceMixin, CaseDocumentSerializer):
    casebody = serializers.SerializerMethodField()

    class Meta:
        document = CaseDocument
        fields = CaseDocumentSerializer.Meta.fields + ('casebody',)
        list_serializer_class = ListSerializerWithCaseAllowance

    def get_casebody(self, case, check_permissions=True):
        # check permissions for full-text access to this case

        request = self.context.get('request')
        if check_permissions:
            status = check_update_case_permissions(request, case)
        else:
            status = 'ok'

        if status == 'ok':
            body_format = request.query_params.get('body_format', None)

            if body_format == 'html':
                data = case.casebody_data['html']
            elif body_format == 'xml':
                data = case.casebody_data['xml']
            elif type(request.accepted_renderer) == HTMLRenderer:
                data = case.casebody_data['html']

            elif type(request.accepted_renderer) == XMLRenderer:
                db_case = models.CaseMetadata.objects.select_related('case_xml').get(pk=case.id)
                try:
                    data = db_case.body_cache.xml
                except CaseBodyCache.DoesNotExist:
                    parsed_xml = db_case.case_xml.get_parsed_xml()
                    db_case.case_xml.reorder_head_matter(parsed_xml)
                    data = helpers.serialize_xml(parsed_xml)
            else:
                try:
                    data = case.casebody_data['text'].to_dict()
                except AttributeError:
                    data = case.casebody_data['text']

            return {
                'data': data,
                'status': status
            }

        return {'status': status, 'data': None}


class VolumeSerializer(serializers.ModelSerializer):
    jurisdictions = JurisdictionSerializer(source='reporter.jurisdictions', many=True)
    reporter_url = serializers.HyperlinkedRelatedField(source='reporter', view_name='reporter-detail', read_only=True)
    reporter = serializers.ReadOnlyField(source='xml_reporter_full_name')
    start_year = serializers.ReadOnlyField(source='spine_start_year')
    end_year = serializers.ReadOnlyField(source='spine_end_year')
    volume_number = serializers.ReadOnlyField(source='xml_volume_number')
    publisher = serializers.ReadOnlyField(source='xml_publisher')
    publication_year = serializers.ReadOnlyField(source='xml_publication_year')

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
        )


class ReporterSerializer(serializers.ModelSerializer):
    jurisdictions = JurisdictionSerializer(many=True)

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
    def get_casebody(self, case):
        """ Tell get_casebody not to check for case download permissions. """
        return super().get_casebody(case, check_permissions=False)

    @property
    def data(self):
        """ Skip tracking of download counts. """
        return super(DocumentSerializer, self).data

class BulkCaseDocumentSerializer(NoLoginCaseDocumentSerializer):
    decision_date = serializers.SerializerMethodField()
    def get_decision_date(self, obj):
        return str(obj.decision_date.date())

