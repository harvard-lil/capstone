import sys
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.exceptions import PermissionDenied
from django.db import models
from django.conf import settings
from django.utils import timezone

from datetime import datetime,timedelta
import uuid

from rest_framework.authtoken.models import Token

class CaseUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Email address is required')

        user = self.model(
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.create_nonce()
        user.save(using=self._db)
        return user


class CaseUser(AbstractBaseUser):
    email = models.EmailField(max_length=254, unique=True, db_index=True,
        error_messages={'unique': u"A user with that email address already exists."})
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_validated = models.BooleanField(default=False)
    case_allowance = models.IntegerField(null=False, blank=False, default=settings.CASE_DAILY_ALLOWANCE)
    is_researcher = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    activation_nonce = models.CharField(max_length=40, null=True, blank=True)
    key_expires = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'

    objects = CaseUserManager()

    class Meta:
        verbose_name = 'User'

    def authenticate_user(self, *args, **kwargs):
        nonce = kwargs.get('activation_nonce')
        if self.activation_nonce == nonce and self.key_expires + timedelta(hours=24) > timezone.now():
            token = Token.objects.create(user=self)
            self.activation_nonce = ''
            self.is_validated = True
            self.save()
        else:
            raise PermissionDenied

    def create_nonce(self):
        self.activation_nonce = self.generate_nonce_timestamp()
        self.key_expires = timezone.now()

    def save(self, *args, **kwargs):
        super(CaseUser, self).save(*args, **kwargs)

    def generate_nonce_timestamp(self):
        nonce = uuid.uuid1()
        return nonce.hex

    def get_api_key(self):
        try:
            return Token.objects.get(user=self).key
        except Exception as e:
            return False

class Case(models.Model):
    caseid = models.CharField(primary_key=True, max_length=255)
    firstpage = models.IntegerField(null=True, blank=True)
    lastpage = models.IntegerField(null=True, blank=True)
    jurisdiction = models.CharField(max_length=100, blank=True)
    citation = models.CharField(max_length=255, blank=True)
    docketnumber = models.CharField(max_length=255, blank=True)
    decisiondate = models.DateField(null=True, blank=True)
    decisiondate_original = models.CharField(max_length=100, blank=True)
    court = models.TextField(blank=True)
    name = models.TextField(blank=True)
    court_abbreviation = models.CharField(max_length=255, blank=True)
    name_abbreviation = models.CharField(max_length=255, blank=True)
    volume = models.CharField(max_length=45, blank=True)
    reporter = models.CharField(max_length=255, blank=True)
    date_added = models.DateTimeField(null=True, blank=True )

    @classmethod
    def create(self, caseid):
        case = self(caseid=caseid)
        return case

    @classmethod
    def create_from_row(self, row):
        try:
            case = Case.objects.get_or_create(caseid=row['caseid'])
            new_timestamp = get_date_added(row['timestamp'])
            if not case.date_added or new_timestamp > case.date_added:
                case.write_case_fields(row)
            return case
        except:
            pass

    def write_case_fields(self, row):
        for prop,val in row.items():
            self.safe_set(prop,val)

        self.decisiondate_original=row['decisiondate_original']

    def safe_set(self, prop, value):
        try:
            if prop == 'decisiondate':
                value = datetime.fromordinal(int(value))
            elif prop == 'timestamp':
                value = get_date_added(value)
                prop = 'date_added'

            setattr(self, prop, value)
            self.save()
        except:
            case_error = CaseError.create(caseid=self.caseid)
            case_error.message = sys.exc_info()[0]
            case_error.field = prop
            case_error.value = value
            if self.date_added:
                case_error.date_added = self.date_added

            case_error.save()
            pass

class CaseError(models.Model):
    field = models.CharField(max_length=45, null=False, blank=False)
    value = models.TextField(null=True, blank=True)
    caseid = models.CharField(max_length=255, null=False, blank=False)
    date_added = models.DateField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    @classmethod
    def create(self, caseid):
        case = self(caseid=caseid)
        return case

def get_date_added(unformatted_timestamp):
    if unformatted_timestamp:
        return datetime.strptime(unformatted_timestamp, "_%Y_%m_%d_%H.%M.%S")
