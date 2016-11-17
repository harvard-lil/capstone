from django.contrib import admin
from .models import *

class CaseUserAdmin(admin.ModelAdmin):
    readonly_fields = ('date_joined','api_key')
    list_display = ('email', 'last_name', 'first_name', 'api_key')
    def api_key(self, instance):
        return instance.get_api_key()
    api_key.short_description = "API Key"
    fields = ('email', 'first_name', 'last_name', 'case_allowance', 'date_joined', 'api_key', 'is_validated', 'is_researcher', 'is_staff')

class CaseAdmin(admin.ModelAdmin):
    list_display = ('name_abbreviation', 'citation')


admin.site.register(Case, CaseAdmin)
admin.site.register(CaseUser, CaseUserAdmin)
