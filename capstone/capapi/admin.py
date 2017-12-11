from django.utils import timezone
from django.contrib import admin
from . import models


def authenticate_user(modeladmin, request, queryset):
    """
    This method will override old key_expires fields by setting it to timezone.now()
    """
    for user in queryset:
        user.key_expires = timezone.now()
        user.authenticate_user(activation_nonce=user.activation_nonce)
        user.save()


authenticate_user.short_description = "Authenticate selected Users"


class APIUserAdmin(admin.ModelAdmin):
    readonly_fields = ('date_joined', 'api_key')
    list_display = ('email', 'last_name', 'first_name', 'api_key', 'total_case_allowance', 'case_allowance_remaining')
    actions = [authenticate_user]

    def api_key(self, instance):
        return instance.get_api_key()

    api_key.short_description = "API Key"


admin.site.register(models.APIUser, APIUserAdmin)
admin.site.register(models.APIToken)
