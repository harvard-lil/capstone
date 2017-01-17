from .models import *
from rest_framework import serializers
from django.core.mail import send_mail
from rest_framework.validators import UniqueValidator
from django.contrib.auth import password_validation, get_user_model
from django.core import exceptions
from resources import email
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

class CaseSerializer(serializers.HyperlinkedModelSerializer):
    jurisdiction_name = serializers.ReadOnlyField(source='jurisdiction.name')
    jurisdiction_id = serializers.ReadOnlyField(source='jurisdiction.id')
    court_name = serializers.ReadOnlyField(source='court.name')
    court_id = serializers.ReadOnlyField(source='court.id')
    reporter_name = serializers.ReadOnlyField(source='reporter.name')
    reporter_id = serializers.ReadOnlyField(source='reporter.id')

    class Meta:
        model = Case
        lookup_field = 'slug'
        fields = ('id', 'slug', 'url',
                  'name', 'name_abbreviation',
                  'citation',
                  'firstpage', 'lastpage',
                  'jurisdiction', 'jurisdiction_name', 'jurisdiction_id',
                  'docketnumber',
                  'decisiondate_original',
                  'court', 'court_name', 'court_id',
                  'reporter', 'reporter_name', 'reporter_id',
                  'volume', 'reporter')
        extra_kwargs = {
            'url': {'lookup_field': 'slug'}
        }

class JurisdictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jurisdiction
        fields = ('id', 'slug', 'name', 'name_abbreviation', )

class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = '__all__'

class ReporterSerializer(serializers.ModelSerializer):
    jurisdiction = serializers.HyperlinkedRelatedField(view_name='jurisdiction-detail', read_only=True)
    jurisdiction_id = serializers.ReadOnlyField(source='jurisdiction.id')
    jurisdiction_name = serializers.ReadOnlyField(source='jurisdiction.name')
    class Meta:
        model = Reporter
        fields = '__all__'

class CourtSerializer(serializers.ModelSerializer):
    jurisdiction = serializers.HyperlinkedRelatedField(view_name='jurisdiction-detail', read_only=True)
    jurisdiction_id = serializers.ReadOnlyField(source='jurisdiction.id')
    jurisdiction_name = serializers.ReadOnlyField(source='jurisdiction.name')
    class Meta:
        model = Court
        lookup_field='id'
        fields = ('id', 'name', 'name_abbreviation', 'jurisdiction', 'jurisdiction_id', 'jurisdiction_name')
        extra_kwargs = {
            'url': {'lookup_field': 'id'}
        }

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseUser
        fields = '__all__'
        read_only_fields = ('is_admin', 'is_researcher', 'activation_key', 'is_validated', 'case_allowance', 'key_expires')
        lookup_field = 'email'

    def verify_with_nonce(self, user_id, activation_nonce):
        found_user = CaseUser.objects.get(pk=user_id)
        if not found_user.is_authenticated():
            found_user.authenticate_user(activation_nonce=activation_nonce)
        return found_user

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
        existing = CaseUser.objects.filter(email=email).first()
        if existing:
            raise serializers.ValidationError("Someone with that email "
                "address has already registered. Was it you?")

        return email

    def validate(self, data):
        if not data.get('password') or not data.get('confirm_password'):
            raise serializers.ValidationError("Please enter a password and "
                "confirm it.")

        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError("Those passwords don't match.")

        return data

    def create(self, validated_data):
        try:
            user = CaseUser.objects.create_user(**validated_data)
            email(reason='new_signup', user=user)
            return user
        except Exception as e:
            raise Exception(e)

class LoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=100,style={'input_type': 'password'})

    class Meta:
        model = CaseUser
        fields = ('email', 'password')
        write_only_fields = ('password')
        lookup_field = 'email'

    def verify_with_password(self, email, password):
        user = CaseUser.objects.get(email=email)
        correct_password = user.check_password(password)
        if not correct_password:
            raise serializers.ValidationError('Invalid password')
        return user
