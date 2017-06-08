import sys
from datetime import datetime, timedelta
import uuid
import logging
import pytz

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models, IntegrityError
from django.utils import timezone
from django.template.defaultfilters import slugify
from rest_framework.authtoken.models import Token

from utils import generate_unique_slug
from . import settings

logger = logging.getLogger(__name__)


class CaseUserManager(BaseUserManager):
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


class CaseUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        max_length=254,
        unique=True,
        db_index=True,
        error_messages={'unique': u"A user with that email address already exists."}
    )
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

    def get_activation_nonce(self):
        if self.key_expires + timedelta(hours=24) < timezone.now():
            self.create_nonce()
            self.save()
        return self.activation_nonce

    def update_case_allowance(self):
        if self.case_allowance_last_updated + timedelta(hours=settings.CASE_EXPIRE_HOURS) < timezone.now():
            self.case_allowance = settings.CASE_DAILY_ALLOWANCE
            self.case_allowance_last_updated = timezone.now()
            self.save()

    def get_case_allowance_update_time_remaining(self):
        td = self.case_allowance_last_updated + timedelta(hours=settings.CASE_EXPIRE_HOURS) - timezone.now()
        return "%sh. %sm." % (td.seconds / 3600, (td.seconds / 60) % 60)

    def authenticate_user(self, **kwargs):
        nonce = kwargs.get('activation_nonce')
        if self.activation_nonce == nonce and self.key_expires + timedelta(hours=24) > timezone.now():
            try:
                Token.objects.create(user=self)
                self.activation_nonce = ''
                self.is_active = True
                self.save()
            except IntegrityError as e:
                logger.warn("IntegrityError in authenticating user: %s %s" % (e, self.email))
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
        except ObjectDoesNotExist:
            return None

    def get_short_name(self):
        return self.email.split('@')[0]


class Volume(models.Model):
    id = models.AutoField(primary_key=True)
    barcode = models.CharField(blank=True, max_length=255)
    number = models.IntegerField(null=True, blank=True, default=None)
    nominative_number = models.IntegerField(null=True, blank=True, default=None)
    date_added = models.DateTimeField(null=True)
    reporter = models.ForeignKey('Reporter', blank=True, null=True, related_name='%(class)s_reporter')
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publication_year = models.IntegerField(null=True, blank=True, default=None)
    start_year = models.IntegerField(null=True, blank=True, default=None)
    end_year = models.IntegerField(null=True, blank=True, default=None)
    pages = models.IntegerField(null=True, blank=True, default=None)
    title = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(null=True)

    @classmethod
    def create_from_tt_row(self, row_num, row):
        # assuming each row is unique
        volume = Volume(id=row_num)
        for key in row.keys():
            try:
                if key == 'bar_code':
                    volume.barcode = row[key]
                elif key == 'volume':
                    volume.number = int(row[key])
                elif key == 'publicationyear':
                    volume.publication_year = int(row[key])
                elif key == 'series_volume':
                    volume.nominative_number = int(row[key])
                elif key == 'reporter_id':
                    try:
                        volume.reporter = Reporter.objects.get(id=row['reporter_id'])
                    except Exception:
                        logger.warn("reporter not found: %s %s" % (row['reporter_id'], volume.barcode))
                        pass
                elif key == 'pages':
                    volume.pages = int(row[key])
                elif key == 'title':
                    volume.title = row['title']
                elif key == 'publisher':
                    volume.publisher = row['publisher']
                else:
                    pass
                volume.save()
            except:
                pass

        start_year = row['page_start_date'] if row['page_start_date'] else row['start_date']
        end_year = row['page_end_date'] if row['page_end_date'] else row['end_date']

        volume.updated_at = datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S")
        try:
            volume.start_year = int(start_year)
            volume.end_year = int(end_year)
            volume.save()
        except:
            pass

        volume.save()

    def safe_set(self, prop, val):
        try:
            setattr(self, prop, val)
            self.save()
        except:
            pass


class Reporter(models.Model):
    id = models.AutoField(primary_key=True)
    jurisdiction = models.ForeignKey('Jurisdiction', blank=True, null=True, related_name='%(class)s_jurisdiction', on_delete=models.SET_NULL)
    name = models.TextField(null=True)
    name_abbreviation = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.IntegerField(blank=True, null=True)
    end_date = models.IntegerField(blank=True, null=True)
    volumes = models.IntegerField(default=0)
    updated_at = models.DateTimeField(null=True)
    slug = models.SlugField(null=True)

    def __unicode__(self):
        return self.slug or ''

    @classmethod
    def create_from_tt_row(self, row):
        reporter, created = Reporter.objects.get_or_create(id=row['id'])
        updated_at = datetime.strptime(row['updated_at'], "%Y-%m-%d %H:%M:%S")

        if created and reporter.updated_at and updated_at and updated_at < reporter.updated_at:
            # return out of func if existing reporter is newer
            return reporter

        jurisdiction, created = Jurisdiction.objects.get_or_create(name_abbreviation=row['state'])
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

    @classmethod
    def get_or_create_unique(self, name, jurisdiction):
        special_cases = {
            'Ct. Cl.': {
                'West Virginia': 'wv-ct-cl',
                'United States': 'us-ct-cl'
            },
            'Smith': {
                'Indiana': 'ind-smith',
                'New Hampshire': 'nh-smith'
            }
        }

        if name in special_cases.keys():
            slug = special_cases[name][jurisdiction]
        else:
            slug = slugify(name)

        try:
            reporter = Reporter.objects.get(name=name, slug=slug)
        except:
            reporter = Reporter(id=Reporter.objects.count(), name=name, slug=slug)

        reporter.save()

        return reporter

    @classmethod
    def get_or_create_from_case(self, name_abbreviation, jurisdiction_id):
        reporter, created = Reporter.objects.get_or_create(name_abbreviation=name_abbreviation, jurisdiction_id=jurisdiction_id)
        reporter.save()
        return reporter


class Jurisdiction(models.Model):
    name = models.CharField(max_length=100, blank=True)
    slug = models.SlugField()
    name_abbreviation = models.CharField(max_length=200, blank=True)

    def __unicode__(self):
        return u"%s" % self.name or ''

    @classmethod
    def create(self, name):
        name = Jurisdiction.fix_common_error(name=name)
        jurisdiction, created = Jurisdiction.objects.get_or_create(name=name)
        if created:
            jurisdiction.slug = slugify(jurisdiction.name_abbreviation)
        jurisdiction.save()
        return jurisdiction

    @classmethod
    def get_or_create_from_case(self, name):
        jur, created = Jurisdiction.objects.get_or_create(name=name)
        jur.save()
        return jur

    @classmethod
    def create_from_tt_row(self, row):
        jurisdiction = Jurisdiction.create(name=row['name'])
        jurisdiction.name_abbreviation = row['name_abbreviation']
        jurisdiction.slug = slugify(jurisdiction.name_abbreviation)
        jurisdiction.save()
        return jurisdiction

    @classmethod
    def fix_common_error(self, name):
        common_errors = {
            'Califonia': 'California',
            'United Statess': 'United States',
            'N.Y.': 'New York',
            '1': 'United States',
            'Philadelphia': 'Pennsylvania',
        }

        if common_errors.get('name'):
            return common_errors[name]
        else:
            return name


class Court(models.Model):
    name = models.CharField(max_length=255)
    name_abbreviation = models.CharField(max_length=100, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='%(class)s_jurisdiction', on_delete=models.SET_NULL)
    slug = models.SlugField()

    def __unicode__(self):
        return u"%s: %s" % (self.id, self.name) or ''

    @classmethod
    def create(self, name, name_abbreviation, jurisdiction):
        court = self(name=name, name_abbreviation=name_abbreviation, jurisdiction=jurisdiction)
        court.slug = slugify(court.name_abbreviation)
        court.save()
        return court

    @classmethod
    def get_or_create_from_case(self, name, name_abbreviation, jurisdiction_id):
        court, created = Court.objects.get_or_create(
                                    name=name,
                                    name_abbreviation=name_abbreviation,
                                    jurisdiction_id=jurisdiction_id
                          )
        court.save()
        return court


class Case(models.Model):
    slug = models.SlugField(unique=True, max_length=255)
    caseid = models.CharField(unique=True, max_length=255)
    firstpage = models.IntegerField(null=True, blank=True)
    lastpage = models.IntegerField(null=True, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='%(class)s_jurisdiction', on_delete=models.SET_NULL)
    citation = models.CharField(max_length=255, blank=True)
    docketnumber = models.CharField(max_length=255, blank=True)
    decisiondate = models.DateField(null=True, blank=True)
    decisiondate_original = models.CharField(max_length=100, blank=True)
    court = models.ForeignKey('Court', null=True, related_name='%(class)s_court', on_delete=models.SET_NULL)
    name = models.TextField(blank=True)
    name_abbreviation = models.CharField(max_length=255, blank=True)
    volume = models.IntegerField(default=0)
    reporter = models.ForeignKey('Reporter', null=True, related_name='%(class)s_reporter', on_delete=models.SET_NULL)
    date_added = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.caseid or ''

    @classmethod
    def create(self, caseid, **kwargs):
        case = self(caseid=caseid, **kwargs)
        case.slug = generate_unique_slug(Case, case.name_abbreviation)
        reporter = Reporter.get_or_create_unique(
                        name=kwargs.get('reporter'),
                        jurisdiction=kwargs.get('jurisdiction')
                   )

        case.reporter = reporter
        case.save()
        return case

    @classmethod
    def create_from_row(self, row):
        try:
            case = Case.objects.get(caseid=row['caseid'])
        except Case.DoesNotExist:
            slug = generate_unique_slug(Case, row['name_abbreviation'])
            case = Case(caseid=row['caseid'], slug=slug)

        # if just created, write fields
        # if already created, check timestamp
        if case.date_added:
            utc = pytz.utc
            naive_timestamp = get_date_added(row['timestamp'])
            if naive_timestamp:
                new_timestamp = utc.localize(naive_timestamp)
                # overwrite case only if:
                # date_added (old timestamp) did not exist and new_timestamp exists
                # timestamp is greater than previous date_added timestamp
                if (new_timestamp and not case.date_added) or (new_timestamp >= case.date_added):
                    case.write_case_fields(row)
        else:
            case.write_case_fields(row)

        case.save()

    def write_case_fields(self, row):
        for prop, val in row.items():
            if prop != 'court' and prop != 'court_abbreviation' and prop != 'reporter':
                self.safe_set(prop, val)

        try:
            jurisdiction_id = self.jurisdiction.id
        except:
            jurisdiction_id = None

        court = Court.get_or_create_from_case(
                        name=row['court'],
                        name_abbreviation=row['court_abbreviation'],
                        jurisdiction_id=jurisdiction_id
                )

        if court:
            self.court = court
            self.save()

        reporter = Reporter.get_or_create_from_case(
                        name_abbreviation=row['reporter'],
                        jurisdiction_id=jurisdiction_id
                   )

        if reporter:
            self.reporter = reporter
            self.save()

        self.safe_set('decisiondate_original', row['decisiondate_original'])

    def safe_set(self, prop, value):
        try:
            if prop == 'decisiondate':
                value = datetime.fromordinal(int(value))
            elif prop == 'jurisdiction':
                value = Jurisdiction.get_or_create_from_case(value)
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
