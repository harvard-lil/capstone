import logging

from django.db import transaction
from rest_framework import serializers
from rest_framework.serializers import ListSerializer

from capdb import models
from .models import CapUser
from .resources import email
from .permissions import get_single_casebody_permissions

logger = logging.getLogger(__name__)


class CitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Citation
        fields = ('type', 'cite', 'normalized_cite')


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


class CaseSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="casemetadata-detail", lookup_field="id")
    court = serializers.ReadOnlyField(source='court.name')
    jurisdiction = JurisdictionSerializer()
    court_url = serializers.HyperlinkedRelatedField(source='court', view_name='court-detail', read_only=True, lookup_field='slug')
    reporter = serializers.ReadOnlyField(source='reporter.full_name')
    reporter_url = serializers.HyperlinkedRelatedField(source='reporter', view_name='reporter-detail', read_only=True)
    citations = CitationSerializer(many=True)
    volume_number = serializers.ReadOnlyField(source='volume.volume_number')
    volume_url = serializers.HyperlinkedRelatedField(source='volume', view_name='volumemetadata-detail', read_only=True)

    class Meta:
        model = models.CaseMetadata
        fields = (
            'id',
            'url',
            'name',
            'name_abbreviation',
            'decision_date',
            'decision_date_original',
            'docket_number',
            'first_page',
            'last_page',
            'citations',
            'jurisdiction',
            'court',
            'court_url',
            'reporter',
            'reporter_url',
            'volume_number',
            'volume_url',
            # 'judges',
            # 'attorneys',
            # 'opinions',
            # 'parties',
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

        with transaction.atomic():
            # for logged-in users, fetch the current user data here inside a transaction, using select_for_update
            # to lock the row so we don't collide with any simultaneous requests
            user = request.user.__class__.objects.select_for_update().get(pk=request.user.pk)

            # update the info for the existing user model, in case it's changed since the request began
            request.user.case_allowance_remaining = user.case_allowance_remaining
            request.user.case_allowance_last_updated = user.case_allowance_last_updated

            result = super().data

            # if user's case allowance was updated, save
            # (this works because it's part of the same transaction with the select_for_update --
            # we don't have to use the same object)
            if request.user.tracker.changed():
                request.user.save()

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

    def get_casebody(self, case):
        request = self.context.get('request')
        casebody = get_single_casebody_permissions(request, case)
        # if getting casebody is allowed set casebody to orig_xml
        # while we figure out what to do with it in our renderers
        # otherwise return casebody obj with status errors
        if casebody['status'] == 'ok':
            casebody['data'] = case.case_xml.orig_xml
        return casebody


class VolumeSerializer(serializers.ModelSerializer):
    jurisdictions = JurisdictionSerializer(source='reporter.jurisdictions', many=True)
    reporter_url = serializers.HyperlinkedRelatedField(source='reporter', view_name='reporter-detail', read_only=True)
    reporter = serializers.ReadOnlyField(source='reporter.full_name')
    start_year = serializers.ReadOnlyField(source='spine_start_year')
    end_year = serializers.ReadOnlyField(source='spine_end_year')

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
            'url',
            'name',
            'name_abbreviation',
            'jurisdiction',
            'jurisdiction_url',
            'slug',
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapUser
        fields = '__all__'
        read_only_fields = ('is_admin', 'is_researcher', 'activation_key', 'is_validated', 'case_allowance_remaining', 'key_expires')
        lookup_field = 'email'

    def verify_with_nonce(self, user_id, activation_nonce):
        found_user = CapUser.objects.get(pk=user_id)
        if not found_user.is_authenticated:
            found_user.authenticate_user(activation_nonce=activation_nonce)
        return found_user

    def verify_case_allowance(self, user, case_count):
        if case_count <= 0:
            return user
        user.update_case_allowance()

        if not user.case_allowance_remaining >= case_count:
            time_remaining = user.get_case_allowance_update_time_remaining()
            raise serializers.ValidationError({
                "error": "You have attempted to download more than your allowed number of cases. Your limit will reset to default again in %s." % time_remaining,
                "case_allowance_remaining": user.case_allowance_remaining,
            })
        else:
            return user


class RegisterUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    password = serializers.CharField(style={'input_type': 'password'})
    confirm_password = serializers.CharField(style={'input_type': 'password'})

    class Meta:
        # write_only_fields = ('password', 'confirm_password')
        fields = '__all__'

    def validate_email(self, email):
        existing = CapUser.objects.filter(email=email).first()
        if existing:
            msg = "Someone with that email address has already registered."
            raise serializers.ValidationError(msg)

        return email

    def validate(self, data):
        if not data.get('password') or not data.get('confirm_password'):
            msg = "Please enter a password and confirm it."
            raise serializers.ValidationError(msg)

        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError("Those passwords don't match.")

        return data

    def create(self, validated_data):
        try:
            email_val = validated_data.pop('email', None)
            password = validated_data.pop('password', None)
            user = CapUser.objects.create_user(email=email_val, password=password, **validated_data)
            email(reason='new_signup', user=user)
            return user
        except Exception as e:
            raise Exception(e)


class LoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=100, style={'input_type': 'password'})

    class Meta:
        model = CapUser
        fields = ('email', 'password')
        write_only_fields = ('password')
        lookup_field = 'email'

    def verify_with_password(self, email, password):
        try:
            user = CapUser.objects.get(email=email)
        except CapUser.DoesNotExist:
            return None
        if user.check_password(password):
            return user
