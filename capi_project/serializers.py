from .models import *
from rest_framework import serializers
from django.core.mail import send_mail
from rest_framework.validators import UniqueValidator


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
        fields = ('password', 'first_name', 'last_name', 'pk', 'email')
        write_only_fields = ('password')
        read_only_fields = ('is_admin', 'is_researcher', 'activation_key', 'is_validated', 'case_allowance', 'key_expires')

    email = serializers.EmailField(
        style={'input_type':'email', 'placeholder':'Email'},
        max_length=100,
    )

    password = serializers.CharField(
        style={'input_type': 'password', 'placeholder': 'Password'},
        write_only=True,
        max_length=100,
    )

    def create(self, validated_data):
        user = self.Meta.model.objects.create_user(**validated_data)
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

    def verify(self, user_id, activation_nonce):
        user = CaseUser.objects.get(pk=user_id)
        user.authenticate_user(activation_nonce=activation_nonce)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        max_length=100,
        style={'placeholder': 'Email'}
    )
    password = serializers.CharField(
        max_length=100,
        style={'input_type': 'password', 'placeholder': 'Password'}
    )
    remember_me = serializers.BooleanField()
