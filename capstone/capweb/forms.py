from django import forms

class ContactForm(forms.Form):
    subject = forms.CharField(label="Message subject", required=True, max_length=100)
    box1 = forms.CharField(label="Do not fill out this box", required=False, widget=forms.Textarea)  # fake message box to fool bots
    box2 = forms.CharField(label="Message content", required=False, widget=forms.Textarea)
    email = forms.EmailField(label="Your email address", required=True)

