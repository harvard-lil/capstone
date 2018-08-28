from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import VolumeXML, CaseXML, PageXML, TrackingToolLog, VolumeMetadata, Reporter, ProcessStep, BookRequest, \
    TrackingToolUser, SlowQuery, Jurisdiction, CaseMetadata, CaseExport


### helpers and setup ###

def new_class(name, *args, **kwargs):
    return type(name, args, kwargs)

# change Django defaults, because 'extra' isn't helpful anymore now you can add more with javascript
admin.TabularInline.extra = 0
admin.StackedInline.extra = 0


### admin models ###

@admin.register(VolumeXML)
class VolumeXMLAdmin(SimpleHistoryAdmin):
    pass


@admin.register(CaseMetadata)
class CaseMetadataAdmin(admin.ModelAdmin):
    list_display = ['name_abbreviation', 'decision_date', 'jurisdiction', 'court', 'reporter']
    list_select_related = ('jurisdiction', 'court', 'reporter')
    inlines = (
        new_class('CaseXMLInline', admin.StackedInline, model=CaseXML),
    )


class CasePageInline(admin.TabularInline):
    model = PageXML.cases.through
    show_change_link = True
    raw_id_fields = ['casexml', 'pagexml']


@admin.register(PageXML)
class PageXMLAdmin(SimpleHistoryAdmin):
    inlines = [CasePageInline]
    exclude = ('cases',)


@admin.register(CaseXML)
class CaseXMLAdmin(SimpleHistoryAdmin):
    inlines = [CasePageInline]


@admin.register(TrackingToolLog)
class TrackingToolLogAdmin(admin.ModelAdmin):
    raw_id_fields = ['volume']


@admin.register(Reporter)
class ReporterAdmin(admin.ModelAdmin):
    pass
    # to inline volumes:
    # inlines = [new_class('VolumeInline', admin.TabularInline, model=VolumeMetadata)]


@admin.register(SlowQuery)
class SlowQueryAdmin(admin.ModelAdmin):
    list_display = ['last_seen', 'label', 'query']
    list_editable = ['label']


@admin.register(Jurisdiction)
class JurisdictionAdmin(admin.ModelAdmin):
    list_display = ['id', 'slug', 'name', 'name_long', 'whitelisted']

@admin.register(CaseExport)
class CaseExportAdmin(admin.ModelAdmin):
    list_display = ['id', 'export_date', 'filter_type', 'filter_id', 'file_name', 'file', 'public']


# models with no admin class yet

admin.site.register(VolumeMetadata)
admin.site.register(ProcessStep)
admin.site.register(BookRequest)
admin.site.register(TrackingToolUser)
