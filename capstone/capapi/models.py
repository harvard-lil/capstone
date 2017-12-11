from datetime import timedelta
import uuid
import logging
import binascii
import os

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError, models
from django.utils import timezone

from django.conf import settings

logger = logging.getLogger(__name__)


class APIUserManager(BaseUserManager):
    def create_user(self, **kwargs):
        email = kwargs.get('email')
        password = kwargs.get('password')
        if not email:
            raise ValueError('Email address is required')

        user = self.model(
            email=self.normalize_email(email),
        )
        user.first_name = kwargs.get('first_name')
        user.last_name = kwargs.get('last_name')
        user.set_password(password)
        user.create_nonce()
        user.save(using=self._db)
        return user


class APIUser(AbstractBaseUser):
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
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    activation_nonce = models.CharField(max_length=40, null=True, blank=True)
    key_expires = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'

    objects = APIUserManager()

    class Meta:
        verbose_name = 'User'

    def get_activation_nonce(self):
        if self.key_expires + timedelta(hours=24) < timezone.now():
            self.create_nonce()
            self.save()
        return self.activation_nonce

    def update_case_allowance(self, case_count=0):
        if self.case_allowance_last_updated + timedelta(hours=settings.API_CASE_EXPIRE_HOURS) < timezone.now():
            self.case_allowance_remaining = self.total_case_allowance
            self.case_allowance_last_updated = timezone.now()

        if case_count:
            self.case_allowance_remaining -= case_count
        self.save(update_fields=['case_allowance_remaining', 'case_allowance_last_updated'])

    def get_case_allowance_update_time_remaining(self):
        td = self.case_allowance_last_updated + timedelta(hours=settings.API_CASE_EXPIRE_HOURS) - timezone.now()
        return "%s hours or %s minutes." % (round(td.seconds / 3600, 2), round((td.seconds / 60) % 60, 2))

    def authenticate_user(self, **kwargs):
        # TODO: make into class method
        nonce = kwargs.get('activation_nonce')
        if self.activation_nonce == nonce and self.key_expires + timedelta(hours=24) > timezone.now():
            try:
                APIToken.objects.create(user=self)
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
        super(APIUser, self).save(*args, **kwargs)

    @staticmethod
    def generate_nonce_timestamp():
        nonce = uuid.uuid1()
        return nonce.hex

    def get_api_key(self):
        try:
            return APIToken.objects.get(user=self).key
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


class APIToken(models.Model):
    # essentially a clone of DRF's Token class
    # we need to create our own Token generating class because DRF's
    # requires the user to be the project's AUTH_USER_MODEL
    # see https://github.com/encode/django-rest-framework/blob/master/rest_framework/authtoken/models.py#L17

    key = models.CharField(max_length=40, primary_key=True)
    user = models.OneToOneField('APIUser')
    created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create(cls, user):
        if user == APIUser.objects.get(pk=user.id):
            token = cls(user=user)
            token.save()
        else:
            raise Exception("Something went wrong when creating token")

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(APIToken, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        return self.key


