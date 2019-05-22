from django import forms
from capapi.models import MailingList


class ContactForm(forms.Form):
    subject = forms.CharField(label="Message subject", required=True, max_length=100)
    message = forms.CharField(label="Message content", required=True, widget=forms.Textarea)
    email = forms.EmailField(label="Your email address", required=True)

class MailingListSubscribe(forms.Form):
    email = forms.EmailField(label="email", required=True)

    def clean_email(self):
        data = self.cleaned_data['email']
        if MailingList.objects.filter(email=data).count() > 0:
            raise forms.ValidationError("You're already subscribed.")
        return data