from django.contrib import admin
from . import models


class APIUserAdmin(admin.ModelAdmin):
    readonly_fields = ('date_joined', 'api_key')
    list_display = ('email', 'last_name', 'first_name', 'api_key')

    def api_key(self, instance):
        return instance.get_api_key()
    api_key.short_description = "API Key"
    fields = (
        'email',
        'first_name',
        'last_name',
        'case_allowance',
        'date_joined',
        'api_key',
        'is_researcher',
        'is_staff'
    )

admin.site.register(models.APIUser, APIUserAdmin)
admin.site.register(models.APIToken)
