from django.utils import timezone
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from capdb.admin import new_class
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
class CapUserAdmin(UserAdmin):
    ## override unhelpful settings from the parent UserAdmin
    ordering = ('-date_joined',)
    filter_horizontal = []
    ## end override

    readonly_fields = ('date_joined',)
    list_display = (
        'email',
        'last_name',
        'first_name',
        'is_staff',
        'unlimited_access_in_effect',
        'case_allowance_remaining',
        'total_case_allowance',
    )
    fieldsets = (
        ('Info', {
            'fields': (
                'email',
                'password',
                'first_name',
                'last_name',
                'date_joined',
            )
        }),
        ('Permissions', {
            'fields': (
                'is_staff',
                'is_active',
                'email_verified',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Access limits', {
            'description': 'If "Unlimited access" is set, user has no quota. If "Unlimited access until" is blank, unlimited '
                           'access lasts forever. Otherwise it expires on that date. If user does not have unlimited access, '
                           'they can download up to "Total case allowance" cases per day. "Case allowance remaining" shows '
                           'how many cases they have downloaded today.',
            'fields': (
                'unlimited_access',
                'harvard_access',
                'unlimited_access_until',
                'total_case_allowance',
                'case_allowance_remaining',
            )
        }),
    )
    search_fields = ('email', 'last_name', 'first_name')
    list_filter = ('research_requests__status', 'research_contracts__status', 'is_staff', 'unlimited_access')
    actions = [authenticate_user]
    inlines = (
        new_class('ResearchContractInline', admin.StackedInline, model=models.ResearchContract, fk_name='user', raw_id_fields=['approver']),
        new_class('HarvardContractInline', admin.StackedInline, model=models.HarvardContract),
        new_class('ResearchRequestInline', admin.StackedInline, model=models.ResearchRequest),
    )

    def unlimited_access_in_effect(self, instance):
        instance._is_harvard_ip = True  # show unlimited access if user would have access given Harvard IP
        return instance.unlimited_access_in_effect()
    unlimited_access_in_effect.short_description = "Unmetered Access"

    def has_add_permission(self, request, obj=None):
        """ We don't currently support adding users via admin -- see Perma code for hints on doing this. """
        return False


@admin.register(models.SiteLimits)
class SiteLimitsAdmin(admin.ModelAdmin):
    list_display = ('id', 'daily_signup_limit', 'daily_signups', 'daily_download_limit', 'daily_downloads')
