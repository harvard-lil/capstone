from django.contrib import admin
from capweb.models import GallerySection, GalleryEntry

from db_file_storage.form_widgets import DBAdminClearableFileInput
from django import forms

class GalleryForm(forms.ModelForm):
    class Meta:
        model = GalleryEntry
        exclude = []
        widgets = {
            'image': DBAdminClearableFileInput
        }

class GalleryAdmin(admin.ModelAdmin):
    list_display = [ "title", "section", "content", "image", "page_link", "repo_link", "order", "featured" ]
    form = GalleryForm


admin.site.register(GalleryEntry, GalleryAdmin)

class GallerySectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'order']


admin.site.register(GallerySection, GallerySectionAdmin)