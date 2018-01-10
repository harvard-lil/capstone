import re
import logging

from rest_framework import serializers

from capdb import models
from .models import APIUser
from .resources import email

logger = logging.getLogger(__name__)


class CitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Citation
        fields = ('url', 'type', 'cite')


class MetaCaseSerializer(serializers.BaseSerializer):
    """
    Serializer for getting case metadata backfilled with the casebody xml
    """

    def to_internal_value(self, case):
        case_metadata = CaseSerializer(case, context=self.context).data
        meta_case = dict(case_metadata)
        case_xml = CaseXMLSerializer(case.case_xml, context=self.context).data
        meta_case['casebody'] = case_xml['casebody']
        return meta_case

    def to_representation(self, obj):
        return obj


class CaseSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="casemetadata-detail",
        lookup_field='slug')
    jurisdiction = serializers.ReadOnlyField(source='jurisdiction.name')
    jurisdiction_url = serializers.HyperlinkedRelatedField(source='jurisdiction', view_name='jurisdiction-detail', read_only=True, lookup_field='slug')
    court = serializers.ReadOnlyField(source='court.name')
    court_url = serializers.HyperlinkedRelatedField(source='court', view_name='court-detail', read_only=True, lookup_field='slug')
    reporter = serializers.ReadOnlyField(source='reporter.full_name')
    reporter_url = serializers.HyperlinkedRelatedField(source='reporter', view_name='reporter-detail', read_only=True)
    citations = CitationSerializer(many=True)
    volume = serializers.ReadOnlyField(source='volume.volume_number')
    volume_url = serializers.HyperlinkedRelatedField(source='volume', view_name='volumemetadata-detail', read_only=True)

    class Meta:
        model = models.CaseMetadata
        fields = (
            'slug',
            'url',
            'name',
            'name_abbreviation',
            'decision_date',
            'docket_number',
            'first_page',
            'last_page',
            'citations',
            'jurisdiction',
            'jurisdiction_url',
            'court',
            'court_url',
            'reporter',
            'reporter_url',
            'volume',
            'volume_url',
        )


class CaseXMLSerializer(serializers.ModelSerializer):
    def get_casebody(self, case):
        casebody = case.get_casebody()
        return re.sub(r"\s{2,}", " ", casebody)

    casebody = serializers.SerializerMethodField()

    class Meta:
        model = models.Citation
        fields = ('casebody',)


class JurisdictionSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="jurisdiction-detail",
        lookup_field='slug')

    class Meta:
        model = models.Jurisdiction
        fields = ('url', 'id', 'slug', 'name', 'name_long')


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
        model = APIUser
        fields = '__all__'
        read_only_fields = ('is_admin', 'is_researcher', 'activation_key', 'is_validated', 'case_allowance_remaining', 'key_expires')
        lookup_field = 'email'

    def verify_with_nonce(self, user_id, activation_nonce):
        found_user = APIUser.objects.get(pk=user_id)
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
        existing = APIUser.objects.filter(email=email).first()
        if existing:
            msg = "Someone with that email address has already registered. Was it you?"
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
            user = APIUser.objects.create_user(**validated_data)
            email(reason='new_signup', user=user)
            return user
        except Exception as e:
            raise Exception(e)


class LoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=100, style={'input_type': 'password'})

    class Meta:
        model = APIUser
        fields = ('email', 'password')
        write_only_fields = ('password')
        lookup_field = 'email'

    def verify_with_password(self, email, password):
        user = APIUser.objects.get(email=email)
        correct_password = user.check_password(password)
        if not correct_password:
            raise serializers.ValidationError('Invalid password')
        return user
