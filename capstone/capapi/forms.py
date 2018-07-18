from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe

from capapi.models import CapUser


class LoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        """ Override AuthenticationForm to block login with unverified email address. """
        if not user.email_verified:
            raise forms.ValidationError(
                mark_safe("This email is registered but not yet verified. <a href='%s'>Resend verification</a>?" % reverse('resend-verification')),
                code='unverified',
            )
        return super().confirm_login_allowed(user)


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=255)


class RegisterUserForm(UserCreationForm):
    class Meta:
        model = CapUser
        fields = ["email", "first_name", "last_name"]

    def clean_email(self):
        """ Ensure that email address doesn't match an existing CapUser.normalized_email. """
        email = self.cleaned_data.get("email")
        if CapUser.objects.filter(normalized_email=CapUser.normalize_email(email)).exists():
            raise forms.ValidationError("A user with the same email address has already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit)
        user.create_nonce()
        return user
