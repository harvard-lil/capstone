from django.contrib import admin
from django.forms.widgets import Textarea
from django.utils.text import normalize_newlines
from simple_history.admin import SimpleHistoryAdmin

from capapi.resources import CachedCountDefaultQuerySet
from .models import VolumeXML, CaseXML, PageXML, TrackingToolLog, VolumeMetadata, Reporter, ProcessStep, BookRequest, \
    TrackingToolUser, SlowQuery, Jurisdiction, CaseMetadata, CaseExport, Citation


### helpers and setup ###

def new_class(name, *args, **kwargs):
    return type(name, args, kwargs)

# change Django defaults, because 'extra' isn't helpful anymore now you can add more with javascript
admin.TabularInline.extra = 0
admin.StackedInline.extra = 0

# ensure that CRLF data from Textareas is normalized to LF
real_textarea_value_from_datadict = Textarea.value_from_datadict
Textarea.value_from_datadict = lambda *a, **k: normalize_newlines(real_textarea_value_from_datadict(*a, **k))


class ReadonlyInlineMixin(object):
    """ Mixin for inlines to not allow editing. """
    can_delete = False

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        result = list(set(
                [field.name for field in self.opts.local_fields] +
                [field.name for field in self.opts.local_many_to_many]
            ))
        result.remove('id')
        return result


class CachedCountMixin(object):
    """
        Mixin for ModelAdmin to use cached .count() queries.
        Admin will report 1000000 entries if the real number is not available.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs.__class__ = CachedCountDefaultQuerySet
        return qs


### admin models ###

@admin.register(VolumeXML)
class VolumeXMLAdmin(SimpleHistoryAdmin):
    raw_id_fields = ['metadata']


@admin.register(CaseMetadata)
class CaseMetadataAdmin(CachedCountMixin, admin.ModelAdmin):
    list_display = ['name_abbreviation', 'decision_date', 'jurisdiction', 'court', 'reporter']
    list_select_related = ('jurisdiction', 'court', 'reporter')
    inlines = (
        new_class('CitationInline', ReadonlyInlineMixin, admin.TabularInline, model=Citation),
        new_class('CaseXMLInline', admin.StackedInline, model=CaseXML, raw_id_fields=['volume']),
    )
    fieldsets = (
        ('Ingest metadata', {
            'fields': ('date_added',)
        }),
        ('Volume and reporter relationship', {
            'description': "These cannot currently be changed via the admin.",
            'fields': ('reporter', 'volume'),
        }),
        ('Metadata from xml', {
            'description': "These values are extracted from the CaseXML, and should be changed there.",
            'fields': ('court', 'jurisdiction', 'attorneys', 'opinions', 'parties', 'judges',
                       'docket_number', 'decision_date', 'decision_date_original', 'name_abbreviation',
                       'name', 'case_id', 'last_page', 'first_page', 'duplicative'),
        }),
        ('Denormalized fields', {
            'description': "Copies of data from related models.",
            'classes': ('collapse',),
            'fields': (
                'jurisdiction_name', 'jurisdiction_whitelisted', 'jurisdiction_slug', 'jurisdiction_name_long',
                'court_slug', 'court_name_abbreviation', 'court_name')
        }),
    )
    # mark all fields as readonly
    readonly_fields = sum((f[1]['fields'] for f in fieldsets), ())


class CasePageInline(admin.TabularInline):
    model = PageXML.cases.through
    show_change_link = True
    raw_id_fields = ['casexml', 'pagexml']


@admin.register(PageXML)
class PageXMLAdmin(CachedCountMixin, SimpleHistoryAdmin):
    inlines = [CasePageInline]
    exclude = ('cases',)
    raw_id_fields = ['volume']


@admin.register(CaseXML)
class CaseXMLAdmin(CachedCountMixin, SimpleHistoryAdmin):
    inlines = [CasePageInline]
    raw_id_fields = ['volume', 'metadata']


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
