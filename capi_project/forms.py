from django.contrib.auth.models import User
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import UserCreationForm

from capi_project.models import CaseUser

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    password = forms.PasswordInput()
    class Meta:
        model = CaseUser
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def clean_email(self):
        try:
            user = CaseUser.objects.get(email__iexact=self.cleaned_data['email'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_("This email already exists. Please try another one."))

    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password'] != self.cleaned_data['password_verification']:
                raise forms.ValidationError(_("The two password fields did not match."))
        return self.cleaned_data
