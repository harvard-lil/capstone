from db_file_storage.form_widgets import DBAdminClearableFileInput

from django.contrib import admin
from django import forms

from capweb.models import GallerySection, GalleryEntry


class GalleryForm(forms.ModelForm):
    class Meta:
        model = GalleryEntry
        exclude = []
        widgets = {
            'image': DBAdminClearableFileInput
        }


@admin.register(GalleryEntry)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "section", "content", "image", "page_link", "repo_link", "order", "featured"]
    list_editable = ["title", "section", "content", "page_link", "repo_link", "order", "featured"]
    list_filter = ["section"]
    form = GalleryForm


@admin.register(GallerySection)
class GallerySectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'order', 'description']
    list_editable = ['title', 'order', 'description']
