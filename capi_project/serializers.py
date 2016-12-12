from .models import *
from rest_framework import serializers
from django.core.mail import send_mail
from rest_framework.validators import UniqueValidator
from django.contrib.auth import password_validation, get_user_model
from django.core import exceptions
from resources import email
class CaseSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        many = kwargs.pop('many', True)
        super(CaseSerializer, self).__init__(many=many, *args, **kwargs)

    class Meta:
        model = Case
        fields = '__all__'

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
        user = CaseUser.objects.create_user(**validated_data)
        email(reason='new_signup', user=user)
        return user


class LoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=100,style={'input_type': 'password', 'placeholder': 'Password'})

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
