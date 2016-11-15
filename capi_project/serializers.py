from .models import *
from rest_framework import serializers
from django.core.mail import send_mail
from rest_framework.validators import UniqueValidator
from django.contrib.auth import password_validation, get_user_model
from django.core import exceptions

class CaseSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        many = kwargs.pop('many', True)
        super(CaseSerializer, self).__init__(many=many, *args, **kwargs)

    class Meta:
        model = Case
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        style={'input_type':'email', 'placeholder':'Email'},
        max_length=100,
        allow_blank=False
    )

    class Meta:
        model = CaseUser
        fields = ('first_name', 'last_name', 'email')
        read_only_fields = ('is_admin', 'is_researcher', 'activation_key', 'is_validated', 'case_allowance', 'key_expires')
        lookup_field = 'email'

    def verify_with_nonce(self, user_id, activation_nonce):
        user = CaseUser.objects.get(pk=user_id)
        user.authenticate_user(activation_nonce=activation_nonce)
        return user


class RegisterUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseUser
        fields = ('email', 'first_name', 'last_name',  'password')
        write_only_fields = ('password')
        lookup_field = 'email'

    def create(self, validated_data):

        user = get_user_model().objects.create_user(**validated_data)

        token_url= "%s/verify-user/%s/%s" % (settings.BASE_URL, user.id, user.activation_nonce)
        send_mail(
            'CaseLaw Access Project: Verify your email address',
            """
                Please click here to verify your email address: %s
            """ % token_url,
            settings.NOREPLY_EMAIL_ADDRESS,
            [user.email],
            fail_silently=False,
        )

        return user

    def validate(self, validated_data):
        password = validated_data.get('password')
        password_confirm = validated_data.get('password_confirm')

        errors = dict()
        try:
            password_validation.validate_password(password=password, user=CaseUser)

        except exceptions.ValidationError as e:
            errors['password'] = list(e.messages)

        if errors:
            raise serializers.ValidationError(errors)

        return super(RegisterUserSerializer, self).validate(validated_data)

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
            raise ValidationError('Invalid password')
        return user
