from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.utils.safestring import mark_safe

from capapi.models import CapUser, ResearchRequest
from capweb.helpers import reverse


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
    agreed_to_tos = forms.BooleanField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # set label here because reverse() isn't ready when defining the class
        self.fields['agreed_to_tos'].label = mark_safe("I have read and agree to the <a href='%s' target='_blank'>Terms of Use</a>." % reverse('terms'))

    class Meta:
        model = CapUser
        fields = ["email", "first_name", "last_name", "password1", "password2", "agreed_to_tos"]

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


class ResearchRequestForm(forms.ModelForm):
    name = forms.CharField(label='Name of researcher')
    institution = forms.CharField(label='Educational or Research Institution')
    title = forms.CharField(label='Title or Affiliation')
    area_of_interest = forms.CharField(label='Research area of interest (optional)', widget=forms.Textarea)

    class Meta:
        model = ResearchRequest
        fields = ["name", "email", "institution", "title", "area_of_interest"]
