from django.contrib import admin

from .models import Volume, Case, Page

def new_class(name, *args, **kwargs):
    return type(name, args, kwargs)

class VolumeAdmin(admin.ModelAdmin):
    pass
admin.site.register(Volume, VolumeAdmin)

class CasePageInline(admin.TabularInline):
    model = Page.cases.through
    show_change_link = True
    raw_id_fields = ['case', 'page']

class PageAdmin(admin.ModelAdmin):
    inlines = [CasePageInline]
    exclude = ('cases',)
admin.site.register(Page, PageAdmin)

class CaseAdmin(admin.ModelAdmin):
    inlines = [CasePageInline]
admin.site.register(Case, CaseAdmin)

# change Django defaults, because 'extra' isn't helpful anymore now you can add more with javascript
admin.TabularInline.extra = 0
admin.StackedInline.extra = 0