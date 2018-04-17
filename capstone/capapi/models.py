from datetime import timedelta
import uuid
import logging

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError, models
from django.utils import timezone
from django.conf import settings

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
        kwargs.setdefault('is_active', True)

        if kwargs.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if kwargs.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email=email, password=password, **kwargs)


class CapUser(AbstractBaseUser):
    email = models.EmailField(
        max_length=254,
        unique=True,
        db_index=True,
        error_messages={'unique': "A user with that email address already exists."}
    )

    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    total_case_allowance = models.IntegerField(null=True, blank=True, default=settings.API_CASE_DAILY_ALLOWANCE)
    case_allowance_remaining = models.IntegerField(null=False, blank=False, default=settings.API_CASE_DAILY_ALLOWANCE)
    # when we last reset the user's case count:
    case_allowance_last_updated = models.DateTimeField(auto_now_add=True)
    is_researcher = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    activation_nonce = models.CharField(max_length=40, null=True, blank=True)
    # TODO: should be renamed nonce_expires

    key_expires = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'

    objects = CapUserManager()
    tracker = FieldTracker()

    class Meta:
        verbose_name = 'User'

    def get_activation_nonce(self):
        if self.key_expires + timedelta(hours=24) < timezone.now():
            self.create_nonce()
            self.save()
        return self.activation_nonce

    def update_case_allowance(self, case_count=0, save=True):
        if self.case_allowance_last_updated + timedelta(hours=settings.API_CASE_EXPIRE_HOURS) < timezone.now():
            self.case_allowance_remaining = self.total_case_allowance
            self.case_allowance_last_updated = timezone.now()

        if case_count:
            if self.case_allowance_remaining < case_count:
                raise AttributeError("Case allowance is too low.")
            self.case_allowance_remaining -= case_count

        if save:
            self.save(update_fields=['case_allowance_remaining', 'case_allowance_last_updated'])

    def get_case_allowance_update_time_remaining(self):
        td = self.case_allowance_last_updated + timedelta(hours=settings.API_CASE_EXPIRE_HOURS) - timezone.now()
        return "%s hours or %s minutes." % (round(td.seconds / 3600, 2), round((td.seconds / 60) % 60, 2))

    def authenticate_user(self, **kwargs):
        nonce = kwargs.get('activation_nonce')
        if self.activation_nonce == nonce and self.key_expires + timedelta(hours=24) > timezone.now():
            try:
                Token.objects.create(user=self)
                self.activation_nonce = ''
                self.is_active = True
                self.save()
            except IntegrityError as e:
                logger.warning("IntegrityError in authenticating user: %s %s" % (e, self.email))
        else:
            raise PermissionDenied

    def create_nonce(self):
        self.activation_nonce = self.generate_nonce_timestamp()
        self.key_expires = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
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

    def has_module_perms(self, app_label):
        if app_label == 'capapi':
            return self.is_staff

        return self.is_superuser

    def has_perm(self, perm, obj=None):
        app, action = perm.split('.')

        if app == 'capapi':
            return self.is_staff

        return self.is_superuser
