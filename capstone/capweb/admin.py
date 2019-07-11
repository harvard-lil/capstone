from django.contrib import admin
from capweb.models import Gallery

class GalleryAdmin(admin.ModelAdmin):
    list_display = ['title', 'content', 'image_path', 'page_link', 'repo_link']
admin.site.register(Gallery, GalleryAdmin)