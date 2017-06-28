from django.contrib import admin

from .models import VolumeXML, CaseXML, PageXML, TrackingToolLog, VolumeMetadata, Reporter, ProcessStep, BookRequest, TrackingToolUser

def new_class(name, *args, **kwargs):
    return type(name, args, kwargs)

class VolumeXMLAdmin(admin.ModelAdmin):
    pass
admin.site.register(VolumeXML, VolumeXMLAdmin)

class CasePageInline(admin.TabularInline):
    model = PageXML.cases.through
    show_change_link = True
    raw_id_fields = ['casexml', 'pagexml']

class PageXMLAdmin(admin.ModelAdmin):
    inlines = [CasePageInline]
    exclude = ('cases',)
admin.site.register(PageXML, PageXMLAdmin)

class CaseXMLAdmin(admin.ModelAdmin):
    inlines = [CasePageInline]
admin.site.register(CaseXML, CaseXMLAdmin)

class TrackingToolLogAdmin(admin.ModelAdmin):
    raw_id_fields = ['volume']
admin.site.register(TrackingToolLog, TrackingToolLogAdmin)

class ReporterAdmin(admin.ModelAdmin):
    pass
    # to inline volumes:
    # inlines = [new_class('VolumeInline', admin.TabularInline, model=VolumeMetadata)]
admin.site.register(Reporter, ReporterAdmin)

admin.site.register(VolumeMetadata)
admin.site.register(ProcessStep)
admin.site.register(BookRequest)
admin.site.register(TrackingToolUser)

# change Django defaults, because 'extra' isn't helpful anymore now you can add more with javascript
admin.TabularInline.extra = 0
admin.StackedInline.extra = 0