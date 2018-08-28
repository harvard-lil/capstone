import logging
import re

from django.db import transaction
from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.serializers import ListSerializer

from capapi.models import SiteLimits
from capapi.renderers import HTMLRenderer, XMLRenderer
from capdb import models
from scripts import helpers
from scripts.generate_case_html import generate_html
from .permissions import get_single_casebody_permissions

logger = logging.getLogger(__name__)


class CitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Citation
        fields = ('type', 'cite')


class CitationWithCaseSerializer(CitationSerializer):
    case_url = serializers.HyperlinkedRelatedField(source='case', view_name='casemetadata-detail',
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


class CourtSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="court-detail",
        lookup_field='slug')

    class Meta:
        model = models.Court
        fields = ('url', 'id', 'slug', 'name', 'name_abbreviation')


class CaseVolumeSerializer(serializers.ModelSerializer):
    """ Abbreviated version of VolumeSerializer for embedding in CaseSerializer. """
    volume_number = serializers.ReadOnlyField(source='xml_volume_number')

    class Meta:
        model = models.VolumeMetadata
        fields = ('url', 'volume_number')


class CaseReporterSerializer(serializers.ModelSerializer):
    """ Abbreviated version of CaseSerializer for embedding in CaseSerializer. """
    class Meta:
        model = models.Reporter
        fields = (
            'url',
            'full_name',
        )


class CaseSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="casemetadata-detail", lookup_field="id")
    court = CourtSerializer(source='denormalized_court')
    jurisdiction = JurisdictionSerializer(source='denormalized_jurisdiction')
    citations = CitationSerializer(many=True)
    volume = CaseVolumeSerializer()
    reporter = CaseReporterSerializer()
    decision_date = serializers.DateField(source='decision_date_original')

    class Meta:
        model = models.CaseMetadata
        fields = (
            'id',
            'url',
            'name',
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
        )


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

        # set request.site_limits so it can be checked later in get_single_casebody_permissions()
        request.site_limits = SiteLimits.get()

        with transaction.atomic():
            # for logged-in users, fetch the current user data here inside a transaction, using select_for_update
            # to lock the row so we don't collide with any simultaneous requests
            user = request.user.__class__.objects.select_for_update().get(pk=request.user.pk)

            # update the info for the existing user model, in case it's changed since the request began
            if not request.user.unlimited_access_in_effect():
                user.update_case_allowance(save=False)  # for SiteLimits, make sure we start with up-to-date user.case_allowance_remaining
                allowance_before = user.case_allowance_remaining
                request.user.case_allowance_remaining = user.case_allowance_remaining
                request.user.case_allowance_last_updated = user.case_allowance_last_updated

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
    """ Custom ListSerializer for CaseSerializerWithCasebody that enforces CaseAllowance. """
    pass


class CaseSerializerWithCasebody(CaseAllowanceMixin, CaseSerializer):
    casebody = serializers.SerializerMethodField()

    class Meta:
        model = CaseSerializer.Meta.model
        fields = CaseSerializer.Meta.fields + ('casebody',)
        list_serializer_class = ListSerializerWithCaseAllowance

    def get_casebody(self, case, check_permissions=True):
        # check permissions for full-text access to this case
        request = self.context.get('request')
        if check_permissions:
            casebody = get_single_casebody_permissions(request, case)
        else:
            casebody = {'status': 'ok', 'data': None}

        if casebody['status'] == 'ok':
            # if status is 'ok', we've passed the perms check and have to load orig_xml into casebody['data']
            orig_xml = case.case_xml.orig_xml

            # non-JSON, single-case delivery formats will be handled by custom renderers
            if type(request.accepted_renderer) == HTMLRenderer:
                data = orig_xml
                casebody['title'] = case.full_cite()
            elif type(request.accepted_renderer) == XMLRenderer:
                data = orig_xml

            # for JSON, pick html, xml, or text based on body_format query param
            else:
                body_format = request.query_params.get('body_format', None)

                if body_format == 'html':
                    # serialize to html
                    data = generate_html(orig_xml)
                elif body_format == 'xml':
                    # serialize to xml
                    casebody_pq = helpers.extract_casebody(orig_xml)

                    # For the XML output, footnotes have <footnote label="foo">, so we should strip "foo" from the start
                    # of the footnote text.
                    for footnote in casebody_pq('casebody|footnote'):
                        label = footnote.attrib.get('label')
                        if label:
                            helpers.left_strip_text(footnote[0], label)

                    c = helpers.serialize_xml(casebody_pq)
                    data = re.sub(r"\s{2,}", " ", c.decode())
                else:
                    # serialize to json
                    casebody_pq = helpers.extract_casebody(orig_xml)

                    # For the plain text output, footnotes should keep their labels in the text, but we want to make sure
                    # there is a space separating the labels from the first word. Otherwise a text analysis comes up with
                    # a lot of noise like "1The".
                    for footnote in casebody_pq('casebody|footnote'):
                        label = footnote.attrib.get('label')
                        if label:
                            # Get text of footnote and replace "[label][nonwhitespace char]" with "[label][nonwhitespace char]"
                            footnote_paragraph = casebody_pq(footnote[0])
                            new_text = footnote_paragraph.text()
                            new_text = re.sub(r'^(%s)(\S)' % re.escape(label), r'\1 \2', new_text)
                            footnote_paragraph.text(new_text)

                    # extract each opinion into a dictionary
                    opinions = []
                    for opinion in casebody_pq.items('casebody|opinion'):
                        opinions.append({
                            'type': opinion.attr('type'),
                            'author': opinion('casebody|author').text() or None,
                            'text': opinion.text(),
                        })

                        # remove opinion so it doesn't get included in head_matter below
                        opinion.remove()

                    data = {
                        'head_matter': casebody_pq.text(),
                        'judges': case.judges,
                        'attorneys': case.attorneys,
                        'parties': case.parties,
                        'opinions': opinions
                    }

            casebody['data'] = data

        return casebody


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
        return reverse('caseexport-download', kwargs={'pk': obj.pk}, request=self.context.get('request'))


# modified serializers for use by scripts/export.py

class BulkJurisdictionSerializer(JurisdictionSerializer):
    class Meta(JurisdictionSerializer.Meta):
        fields = [field for field in JurisdictionSerializer.Meta.fields if field not in ('url',)]

class BulkCourtSerializer(CourtSerializer):
    class Meta(CourtSerializer.Meta):
        fields = [field for field in CourtSerializer.Meta.fields if field not in ('url',)]

class BulkCaseVolumeSerializer(CaseVolumeSerializer):
    class Meta(CaseVolumeSerializer.Meta):
        fields = [field for field in CaseVolumeSerializer.Meta.fields if field not in ('url',)]

class BulkCaseReporterSerializer(CaseReporterSerializer):
    class Meta(CaseReporterSerializer.Meta):
        fields = [field for field in CaseReporterSerializer.Meta.fields if field not in ('url',)]

class BulkCaseSerializer(CaseSerializerWithCasebody):
    court = BulkCourtSerializer(source='denormalized_court')
    jurisdiction = BulkJurisdictionSerializer(source='denormalized_jurisdiction')
    volume = BulkCaseVolumeSerializer()
    reporter = BulkCaseReporterSerializer()

    class Meta(CaseSerializerWithCasebody.Meta):
        model = models.CaseMetadata
        fields = [field for field in CaseSerializerWithCasebody.Meta.fields if field not in ('url',)]

    def get_casebody(self, case):
        """ Tell get_casebody not to check for case download permissions. """
        return super().get_casebody(case, check_permissions=False)

    @property
    def data(self):
        """ Skip tracking of download counts. """
        return super(serializers.HyperlinkedModelSerializer, self).data
