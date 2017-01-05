import sys
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError
from django.template.defaultfilters import slugify

from datetime import datetime,timedelta
import pytz
import uuid
import logging
from random import randint

from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)

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

class Volume(models.Model):
    barcode = models.IntegerField(unique=True)
    number = models.IntegerField(blank=True)
    nominative_number = models.IntegerField(blank=True, null=True)
    date_added = models.DateTimeField()
    reporter = models.ForeignKey('Reporter', blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True)
    publication_year = models.IntegerField(blank=True, null=True)
    start_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    pages = models.IntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(null=True)

    @classmethod
    def create_from_tt_row(self, row):
        volume, created = Volume.objects.get_or_create(id=id)
        updated_at = datetime.strptime(row['updated_at'], "%m/%d/%Y %I:%M:%S %p")

        if not created and updated_at < volume.updated_at:
            # return out of func if existing volume is newer
            return volume
        volume.barcode = row['bar_code']
        volume.reporter = Reporter.objects.get(id=row['reporter_id'])
        volume.publication_year = row['publicationyear']
        volume.number = row['volume']
        volume.nominative_number = row['series_volume']
        volume.start_year = row['page_start_date'] if row['page_start_date'] else row['start_date']
        volume.end_year = row['page_end_date'] if row['page_end_date'] else row['end_date']
        volume.pages = row['pages']
        volume.title = row['title']
        volume.publisher = row['publisher']



class Reporter(models.Model):
    id = models.IntegerField(primary_key=True)
    jurisdiction = models.SlugField(max_length=100, null=True)
    jurisdiction_name = models.ForeignKey('Jurisdiction', blank=True, null=True)
    name_abbreviation = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.IntegerField(blank=True, null=True)
    end_date = models.IntegerField(blank=True, null=True)
    volumes = models.IntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(null=True)
    name = models.CharField(max_length=255, null=True)
    slug = models.SlugField(unique=True, max_length=100, null=True)

    def __unicode__(self):
        return self.slug

    @classmethod
    def create_from_tt_row(self, row):
        reporter, created = Reporter.objects.get_or_create(id=id)
        updated_at = datetime.strptime(row['updated_at'], "%m/%d/%Y %I:%M:%S %p")

        if not created and updated_at < reporter.updated_at:
            # return out of func if existing reporter is newer
            return reporter

        import ipdb; ipdb.set_trace()
        jurisdiction = Jurisdiction.objects.get_or_create(name_abbreviation=row['state'])
        jurisdiction.slug = slugify(jurisdiction.name_abbreviation)
        jurisdiction.save()
        reporter.jurisdiction = jurisdiction
        reporter.name = row['reporter']
        reporter.name_abbreviation = row['short']
        reporter.start_date = row['start_date']
        reporter.end_date = row['end_date']
        reporter.volumes = row['volumes']
        reporter.updated_at = updated_at
        reporter.slug = slugify(reporter.name_abbreviation)

        reporter.save()

        return reporter
        # except Exception as e:
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

        reporter, created = Reporter.objects.get_or_create(name=case.reporter, slug=slug)

        if not created:
            reporter.save()
        case.reporter = reporter
        case.save()

        return reporter

class Jurisdiction(models.Model):
    name = models.CharField(unique=True, max_length=100, blank=True)
    slug = models.SlugField(unique=True)
    name_abbreviation = models.CharField(max_length=200, blank=True, unique=True)

    @classmethod
    def create(self, name):
        # import ipdb; ipdb.set_trace()
        name = Jurisdiction.fix_common_error(name=name)
        jurisdiction, created = Jurisdiction.objects.get_or_create(name=name)
        if created:
            jurisdiction.name_abbreviation = name_abbreviation
            jurisdiction.slug = slugify(name_abbreviation)
        jurisdiction.save()
        return jurisdiction

    @classmethod
    def create_from_tt_row(self, row):
        jurisdiction = Jurisdiction.create(name=row['name'],name_abbreviation=row['name_abbreviation'])
        jurisdiction.save()
        return jurisdiction

    @classmethod
    def fix_common_error(self, name):
        common_errors = {
                'Califonia':'California',
                'United Statess': 'United States',
                'N.Y.': 'New York',
                '1': 'United States',
                'Philadelphia':'Pennsylvania',
            }

        if common_errors.get('name'):
            return common_errors[name]
        else:
            return name

class Court(models.Model):
    name = models.CharField(max_length=255)
    name_abbreviation = models.CharField(max_length=100, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True)
    slug = models.SlugField()

    @classmethod
    def create(self, name, name_abbreviation, jurisdiction):
        court = self(name=name, name_abbreviation=name_abbreviation, jurisdiction=jurisdiction)
        court.slug = slugify(court.name_abbreviation)
        court.save()
        return court

class Case(models.Model):
    caseid = models.CharField(primary_key=True, max_length=255)
    firstpage = models.IntegerField(null=True, blank=True)
    lastpage = models.IntegerField(null=True, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True)
    citation = models.CharField(max_length=255, blank=True)
    docketnumber = models.CharField(max_length=255, blank=True)
    decisiondate = models.DateField(null=True, blank=True)
    decisiondate_original = models.CharField(max_length=100, blank=True)
    court = models.TextField(blank=True)
    court_name = models.ForeignKey('Court', null=True)
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
        case.slug = self.create_slug(case.name_abbreviation)
        reporter = Reporter.create_unique(name=kwargs.get('reporter'), jurisdiction=kwargs.get('jurisdiction'))
        case.reporter = reporter
        case.save()
        return case

    def create_slug(name_abbr):
        rand_num = randint(1000,10000)
        slug = "%s-%s" % (slugify(name_abbr),rand_num)
        # check for uniqueness
        if Case.objects.get(slug=slug):
            # if case exists, call again
            self.create_slug(name_abbr)
        else:
            return slug

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
            elif prop == 'jurisdiction':
                value = self.get_jurisdiction(val)

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

    def get_jurisdiction(self, jurisdiction):
        jur = Jurisdiction.objects.filter(name__icontains=jurisdiction)
        if len(jur):
            return list(jur)[0]
        else:
            return Jurisdiction.objects.create(name=jurisdiction)


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
