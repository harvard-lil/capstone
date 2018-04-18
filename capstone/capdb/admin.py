from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import VolumeXML, CaseXML, PageXML, TrackingToolLog, VolumeMetadata, Reporter, ProcessStep, BookRequest, \
    TrackingToolUser, SlowQuery


def new_class(name, *args, **kwargs):
    return type(name, args, kwargs)


class VolumeXMLAdmin(SimpleHistoryAdmin):
    pass


class CasePageInline(admin.TabularInline):
    model = PageXML.cases.through
    show_change_link = True
    raw_id_fields = ['casexml', 'pagexml']


class PageXMLAdmin(SimpleHistoryAdmin):
    inlines = [CasePageInline]
    exclude = ('cases',)


class CaseXMLAdmin(SimpleHistoryAdmin):
    inlines = [CasePageInline]


class TrackingToolLogAdmin(admin.ModelAdmin):
    raw_id_fields = ['volume']


class ReporterAdmin(admin.ModelAdmin):
    pass
    # to inline volumes:
    # inlines = [new_class('VolumeInline', admin.TabularInline, model=VolumeMetadata)]


class SlowQueryAdmin(admin.ModelAdmin):
    list_display = ['last_seen', 'label', 'query']
    list_editable = ['label']


admin.site.register(VolumeXML, VolumeXMLAdmin)
admin.site.register(PageXML, PageXMLAdmin)
admin.site.register(CaseXML, CaseXMLAdmin)
admin.site.register(TrackingToolLog, TrackingToolLogAdmin)
admin.site.register(Reporter, ReporterAdmin)
admin.site.register(SlowQuery, SlowQueryAdmin)
admin.site.register(VolumeMetadata)
admin.site.register(ProcessStep)
admin.site.register(BookRequest)
admin.site.register(TrackingToolUser)

# change Django defaults, because 'extra' isn't helpful anymore now you can add more with javascript
admin.TabularInline.extra = 0
admin.StackedInline.extra = 0
