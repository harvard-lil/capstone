from django.contrib import admin
from capweb.models import GallerySection, GalleryEntry

class GalleryAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'content', 'image', 'page_link', 'repo_link']

admin.site.register(GalleryEntry, GalleryAdmin)


class GallerySectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'order']


admin.site.register(GallerySection, GallerySectionAdmin)