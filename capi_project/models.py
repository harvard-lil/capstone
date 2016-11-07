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

    @classmethod
    def create(self, caseid):
        case = self(caseid=caseid)
        return case

    @classmethod
    def create_from_row(self, row):
        d = int(row['decisiondate'])
        decisiondate = datetime.fromordinal(d)

        case = self(
            caseid=row['caseid'],
            firstpage=row['firstpage'],
            lastpage=row['lastpage'],
            jurisdiction=row['jurisdiction'],
            citation=row['citation'],
            docketnumber=row['docketnumber'],
            decisiondate=decisiondate,
            decisiondate_original=row['decisiondate_original'],
            court=row['court'],
            name=row['name'],
            court_abbreviation=row['court_abbreviation'],
            name_abbreviation=row['name_abbreviation'],
            volume=row['volume'],
            reporter=row['reporter'],
            )

        case.save()
        return case
