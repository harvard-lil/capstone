from django import forms

class ContactForm(forms.Form):
    subject = forms.CharField(label="Message subject", required=True, max_length=100)
    message = forms.CharField(label="Message content", required=True, widget=forms.Textarea)
    email = forms.EmailField(label="Your email address", required=True)

