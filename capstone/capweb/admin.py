from django.contrib import admin
from capweb.models import Gallery

class GalleryAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'content', 'image', 'page_link', 'repo_link']
admin.site.register(Gallery, GalleryAdmin)