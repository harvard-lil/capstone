from datetime import timedelta
import uuid
import logging

import email_normalize
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, AnonymousUser, PermissionsMixin
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models, IntegrityError, transaction
from django.utils import timezone
from django.conf import settings
from netaddr import IPAddress, AddrFormatError, IPNetwork

from model_utils import FieldTracker

from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class CapUserManager(BaseUserManager):
    def create_user(self, email, password, **kwargs):
        if not email:
            raise ValueError('Email address is required')

        user = self.model(email=self.normalize_email(email), **kwargs)
        user.set_password(password)
        user.create_nonce()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **kwargs):
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)
        kwargs.setdefault('email_verified', True)
        kwargs.setdefault('total_case_allowance', settings.API_CASE_DAILY_ALLOWANCE)
        kwargs.setdefault('case_allowance_remaining', settings.API_CASE_DAILY_ALLOWANCE)

        if kwargs.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if kwargs.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email=email, password=password, **kwargs)

# This is a temporary workaround for the problem described in
# https://github.com/jazzband/django-model-utils/issues/331#issuecomment-478994563
# where django-model-utils FieldTracker breaks the setter for overridden attributes on abstract base classes
del AbstractBaseUser.is_active

class CapUser(PermissionsMixin, AbstractBaseUser):
    email = models.EmailField(
        max_length=254,
        unique=True,
        db_index=True,
        error_messages={'unique': "A user with that email address already exists."}
    )
    normalized_email = models.CharField(max_length=255, help_text="Used to ensure that new emails are unique.")

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    total_case_allowance = models.IntegerField(null=True, blank=True, default=0)
    case_allowance_remaining = models.IntegerField(null=False, blank=False, default=0)
    # when we last reset the user's case count:
    case_allowance_last_updated = models.DateTimeField(auto_now_add=True)
    unlimited_access = models.BooleanField(default=False)
    harvard_access = models.BooleanField(default=False)
    unlimited_access_until = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    email_verified = models.BooleanField(default=False, help_text="Whether user has verified their email address")
    activation_nonce = models.CharField(max_length=40, null=True, blank=True)
    nonce_expires = models.DateTimeField(null=True, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True)
    agreed_to_tos = models.BooleanField(default=False)

    # this has not been backfilled to be accurate for people who signed up for the mailing list before late dec of 2019
    # you should use the MailChimp campaign for a more accurate list.
    mailing_list = models.BooleanField(default=False)

    deactivated_by_user = models.BooleanField(default=False)
    deactivated_date = models.DateTimeField(null=True, auto_now_add=False)

    USERNAME_FIELD = 'email'

    objects = CapUserManager()
    tracker = FieldTracker()

    class Meta:
        verbose_name = 'User'

    def get_activation_nonce(self):
        if self.nonce_expires + timedelta(hours=24) < timezone.now():
            self.create_nonce()
            self.save()
        return self.activation_nonce

    def unlimited_access_in_effect(self):
        return (
            (
                self.unlimited_access or
                (self.harvard_access and self.harvard_ip())
            ) and (
                self.unlimited_access_until is None or
                self.unlimited_access_until > timezone.now()
            )
        )

    def harvard_ip(self):
        """ Return True if X-Forwarded-For header is a Harvard IP address. """
        if not hasattr(self, '_is_harvard_ip'):
            try:
                ip = IPAddress(self.ip_address)  # set by AuthenticationMiddleware
            except AddrFormatError:
                self._is_harvard_ip = False
            else:
                self._is_harvard_ip = any(IPAddress(ip) in IPNetwork(ip_range) for ip_range in settings.HARVARD_IP_RANGES)
        return self._is_harvard_ip

    def update_case_allowance(self, case_count=0, save=True):
        if self.unlimited_access_in_effect():
            return

        if self.case_allowance_last_updated + timedelta(hours=settings.API_CASE_EXPIRE_HOURS) < timezone.now():
            self.case_allowance_remaining = self.total_case_allowance
            self.case_allowance_last_updated = timezone.now()

        if case_count:
            if self.case_allowance_remaining < case_count:
                raise AttributeError("Case allowance is too low.")
            self.case_allowance_remaining -= case_count

        if save:
            self.save(update_fields=['case_allowance_remaining', 'case_allowance_last_updated'])

    def authenticate_user(self, activation_nonce):
        if self.activation_nonce == activation_nonce and self.nonce_expires + timedelta(hours=24) > timezone.now():
            Token.objects.create(user=self)
            self.activation_nonce = ''
            self.email_verified = True
            self.save()
        else:
            raise PermissionDenied

    def reset_api_key(self):
        if self.get_api_key() and self.email_verified:
            Token.objects.get(user=self).delete()
            Token.objects.create(user=self)
            self.save()
        else:
            raise PermissionDenied

    def create_nonce(self):
        self.activation_nonce = self.generate_nonce_timestamp()
        self.nonce_expires = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if self.tracker.has_changed('email'):
            self.normalized_email = self.normalize_email(self.email)
        if self.tracker.has_changed('is_active') and not self.is_active:
            self.deactivated_date = timezone.now()
        super(CapUser, self).save(*args, **kwargs)

    @staticmethod
    def generate_nonce_timestamp():
        nonce = uuid.uuid1()
        return nonce.hex

    def get_api_key(self):
        try:
            # relying on DRF's Token model
            return self.auth_token.key
        except ObjectDoesNotExist:
            return None

    def get_short_name(self):
        return self.email.split('@')[0]

    def case_download_allowed(self, case_count):
        if case_count > 0:
            self.update_case_allowance()
            return self.case_allowance_remaining >= case_count
        else:
            return True

    @staticmethod
    def normalize_email(email):
        """
            Return a normalized form of the email address:
            - lowercase
            - applying host-specific rules for domains hosted by Google, Microsoft, Yahoo, Fastmail
        """
        return email_normalize.normalize(email.strip(), resolve=False)


# make AnonymousUser API conform with CapUser API
AnonymousUser.unlimited_access_until = None
AnonymousUser.unlimited_access_in_effect = lambda self: False


class ResearchRequest(models.Model):
    """ Request for research access submitted by an unaffiliated user. """
    user = models.ForeignKey(CapUser, on_delete=models.CASCADE, related_name='research_requests')
    submitted_date = models.DateTimeField(auto_now_add=True)

    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    institution = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    area_of_interest = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, default='pending', verbose_name="research request status",
                              choices=(('pending', 'pending'), ('approved', 'approved'), ('denied', 'denied'), ('awaiting signature', 'awaiting signature')))
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_date']


class ResearchContract(models.Model):
    """ Signed application for access submitted by an affiliated researcher. """
    user = models.ForeignKey(CapUser, on_delete=models.CASCADE, related_name='research_contracts')
    user_signature_date = models.DateTimeField(auto_now_add=True)

    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    institution = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    area_of_interest = models.TextField(blank=True, null=True)

    contract_html = models.TextField(blank=True, null=True)

    approver = models.ForeignKey(CapUser, blank=True, null=True, on_delete=models.DO_NOTHING, related_name='approved_contracts')
    approver_signature_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending', verbose_name="research contract status",
                              choices=(('pending', 'pending'), ('approved', 'approved'), ('denied', 'denied')))
    approver_notes = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-user_signature_date']


class HarvardContract(models.Model):
    """ Signed access contract submitted by a Harvard user. """
    user = models.ForeignKey(CapUser, on_delete=models.CASCADE, related_name='harvard_contracts')
    user_signature_date = models.DateTimeField(auto_now_add=True)

    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    title = models.CharField(max_length=255)
    area_of_interest = models.TextField(blank=True, null=True)

    contract_html = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-user_signature_date']



class SiteLimits(models.Model):
    """
        Singleton model to track sitewide values in a row with ID=1
    """
    daily_signup_limit = models.IntegerField(default=50)
    daily_signups = models.IntegerField(default=0)
    daily_download_limit = models.IntegerField(default=50000)
    daily_downloads = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Site limits"

    @classmethod
    def create(cls):
        """ Create and return the ID=1 row, or fetch the existing one. """
        site_limits = cls(pk=1)
        try:
            site_limits.save()
        except IntegrityError:
            return cls.objects.get(pk=1)
        else:
            return site_limits

    @classmethod
    def get(cls):
        """ Get the ID=1 row, creating if necessary. """
        try:
            return cls.objects.get(pk=1)
        except cls.DoesNotExist:
            return cls.create()

    @classmethod
    def get_for_update(cls):
        """
            Get the ID=1 row with select_for_update()
            This must be run from within a transaction.
        """
        try:
            site_limits = cls.objects.select_for_update().get(pk=1)
        except cls.DoesNotExist:
            cls.create()
            site_limits = cls.objects.select_for_update().get(pk=1)
        return site_limits

    @classmethod
    def add_values(cls, **pairs):
        """
            Modify existing values.
            E.g., SiteLimits.add_values(daily_downloads=1) increases daily_downloads by 1.
        """
        with transaction.atomic():
            site_limits = cls.get_for_update()
            for k, v in pairs.items():
                setattr(site_limits, k, getattr(site_limits, k) + v)
            site_limits.save()
        return site_limits

    @classmethod
    def reset(cls):
        """ Reset all counters to 0. """
        with transaction.atomic():
            site_limits = cls.get_for_update()
            site_limits.daily_signups = 0
            site_limits.daily_downloads = 0
            site_limits.save()


class MailingList(models.Model):
    email = models.EmailField(
        max_length=254,
        unique=True,
        error_messages={'unique': "You're already subscribed."}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # this field could be manually set in the unlikely case that someone repeatedly signs someone else up. They couldn't
    # re-add the address since their it would already be in here, but we'd know to not email them.
    do_not_email = models.BooleanField(default=False)
