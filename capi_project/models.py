import sys
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError

from datetime import datetime,timedelta
import pytz
import uuid

from rest_framework.authtoken.models import Token

class CaseUserManager(BaseUserManager):
    def create_user(self, *args, **kwargs):
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

class CaseUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=254, unique=True, db_index=True,
        error_messages={'unique': u"A user with that email address already exists."})
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    case_allowance = models.IntegerField(null=False, blank=False, default=settings.CASE_DAILY_ALLOWANCE)
    case_allowance_last_updated = models.DateTimeField(auto_now_add=True)
    is_researcher = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    activation_nonce = models.CharField(max_length=40, null=True, blank=True)
    key_expires = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'

    objects = CaseUserManager()

    class Meta:
        verbose_name = 'User'

    def get_activation_nonce(self, *args, **kwargs):
        if self.key_expires + timedelta(hours=24) < timezone.now():
            self.create_nonce()
            self.save()
        return self.activation_nonce

    def update_case_allowance(self, *args, **kwargs):
        if self.case_allowance_last_updated + timedelta(hours=settings.CASE_EXPIRE_HOURS) < timezone.now():
            self.case_allowance = settings.CASE_DAILY_ALLOWANCE
            self.case_allowance_last_updated = timezone.now()
            self.save()

    def authenticate_user(self, *args, **kwargs):
        nonce = kwargs.get('activation_nonce')
        if self.activation_nonce == nonce and self.key_expires + timedelta(hours=24) > timezone.now():
            try:
                token = Token.objects.create(user=self)
                self.activation_nonce = ''
                self.is_active = True
                self.save()
            except IntegrityError as e:
                print "IntegrityError in authenticating user:",e,self.email
                pass
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

    def get_short_name(self):
        return self.email.split('@')[0]

class Reporter(models.Model):
    name = models.CharField(max_length=255, null=True)
    slug = models.SlugField(unique=True, max_length=100)
    jurisdiction = models.SlugField(max_length=100, null=True)

    def __unicode__(self):
        return self.slug

    @classmethod
    def create_unique(self, name, jurisdiction):
        special_cases =  {
                'Ct. Cl.':  {
                    'West Virginia':'wv-ct-cl', 'United States': 'us-ct-cl'},
                'Smith': {
                    'Indiana':'ind-smith', 'New Hampshire':'nh-smith'
                }
            }
        if case.reporter in special_cases:
            slug = special_cases[case.reporter][case.jurisdiction]
        else:
            slug = slugify(case.reporter)

        reporter, created = Reporter.objects.get_or_create(name=case.reporter, slug=slug, jurisdiction=slugify(case.jurisdiction))

        if not created:
            reporter.save()
        case.reporter_name = reporter
        case.save()

        return reporter

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
    slug = models.SlugField(blank=True)
    volume = models.IntegerField(blank=True)
    reporter = models.ForeignKey('Reporter', null=True)
    date_added = models.DateTimeField(null=True, blank=True )

    def __unicode__(self):
        return self.caseid

    @classmethod
    def create(self, caseid, **kwargs):
        case = self(caseid=caseid, **kwargs)
        case.slug = slugify(case.name_abbreviation)
        reporter = Reporter.create_unique(name=kwargs.get('reporter'), jurisdiction=kwargs.get('jurisdiction'))
        case.reporter = reporter
        case.save()
        return case

    @classmethod
    def create_from_row(self, row):
        try:
            case, created = Case.objects.get_or_create(caseid=row['caseid'])
            if not created:
                case.write_case_fields(row)
            else:
                utc = pytz.utc
                naive_timestamp = get_date_added(row['timestamp'])
                if naive_timestamp:
                    new_timestamp = utc.localize(naive_timestamp)
                    # overwrite case only if:
                    # date_added (old timestamp) did not exist and new_timestamp exists
                    # timestamp is greater than previous date_added timestamp
                    if (new_timestamp and not case.date_added) or (new_timestamp > case.date_added):
                        case.write_case_fields(row)
                else:
                    # case has already been created and we are iterating
                    # over the same row again (without date_added)
                    pass

        except Exception as e:
            print "Exception caught on case creation: %s" % e
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
                utc = pytz.utc
                if value:
                    value = utc.localize(value)
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
