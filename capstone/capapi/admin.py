from django.utils import timezone
from django.contrib import admin

from . import models


def authenticate_user(modeladmin, request, queryset):
    """
    This method will override old nonce_expires fields by setting it to timezone.now()
    """
    for user in queryset:
        user.nonce_expires = timezone.now()
        user.authenticate_user(activation_nonce=user.activation_nonce)
        user.save()


authenticate_user.short_description = "Authenticate selected Users"


@admin.register(models.CapUser)
class CapUserAdmin(admin.ModelAdmin):
    readonly_fields = ('date_joined', 'api_key', 'unlimited_access')
    list_display = (
        'email',
        'last_name',
        'first_name',
        'is_staff',
        'api_key',
        'unlimited_access',
        'case_allowance_remaining',
        'total_case_allowance',
    )

    fields = list_display + ('is_active', 'email_verified', 'date_joined', 'activation_nonce', 'unlimited_access_until')
    actions = [authenticate_user]

    def unlimited_access(self, instance):
        return instance.unlimited_access_in_effect()

    def api_key(self, instance):
        return instance.get_api_key()

    api_key.short_description = "API Key"
    unlimited_access.short_description = "Unlimited Access"


@admin.register(models.ResearchRequest)
class ResearchRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'submitted_date', 'status', 'name', 'email', 'institution', 'title')
    raw_id_fields = ('user',)
    list_filter = ('status',)