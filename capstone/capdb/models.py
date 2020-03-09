import hashlib
import itertools
import json
import math
import re
from contextlib import contextmanager
import struct
import base64
import fitz
from lxml import etree
from model_utils import FieldTracker
import nacl
import nacl.encoding
import nacl.secret
from pyquery import PyQuery
from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, IntegrityError, transaction
from django.db.models import Q
from django.utils.text import slugify
from django.utils.encoding import force_bytes, force_str
from django.core.files.base import ContentFile

from capdb.storages import bulk_export_storage, case_image_storage, download_files_storage
from capdb.versioning import TemporalHistoricalRecords, TemporalQuerySet
from capweb.helpers import reverse, transaction_safe_exceptions
from scripts import render_case
from scripts.fix_court_tag.fix_court_tag import fix_court_tag
from scripts.helpers import (special_jurisdiction_cases, jurisdiction_translation, parse_xml,
                             serialize_xml, jurisdiction_translation_long_name,
                             short_id_from_s3_key)
from scripts.process_metadata import get_case_metadata, parse_decision_date


def choices(*args):
    """ Simple helper to create choices=(('Foo','Foo'),('Bar','Bar'))"""
    return zip(args, args)


def fetch_relations(instance, select_relations=None, prefetch_relations=None):
    """
        Load attributes on instance as though they had been loaded by objects.select_related() and object.prefetch_related().
        For example, these are equivalent, with the second taking one more SQL query:

            instance = Model.objects.select_related('foo__bar', 'baz').prefetch_related('bang').get(pk=1)

        And:

            instance = Model.objects.get(pk=1)
            fetch_relations(instance, select_relations=['foo__bar', 'baz'], prefetch_relations=['bang'])

    """
    select_relations = select_relations or []
    prefetch_relations = prefetch_relations or []

    # filter out any relations that have already been loaded
    def filter_relations(relations, kind):
        non_loaded_relations = []
        field_names = []
        for relation in relations:
            relation_parts = relation.split('__', 1)
            field_name, sub_relation = relation_parts[0], relation_parts[1:]

            # fetch the field referred to by this field_name
            field = instance._meta.get_field(field_name)
            assert field.is_relation, "%s is not a foreign field" % field_name

            # if this is a forward relation with no ID set, we can cache the None value immediately,
            # and there is no need to fetch anything
            if hasattr(field, 'get_local_related_value') and None in field.get_local_related_value(instance):
                getattr(instance, field_name)
                continue

            # if this is a prefetch field that's already prefetched, no need to fetch anything
            if kind == 'prefetch_relations' and not sub_relation and hasattr(instance, '_prefetched_objects_cache') and field_name in instance._prefetched_objects_cache:
                continue

            # if field isn't cached, we should fetch it
            if not field.is_cached(instance):
                non_loaded_relations.append(relation)
                field_names.append(field_name)

            # if field is cached, we can't safely fetch subrelations ourselves, so call fetch_relations recursively
            elif sub_relation:
                fetch_relations(getattr(instance, field_name), **{kind: sub_relation})

        return non_loaded_relations, field_names

    select_relations, select_field_names = filter_relations(select_relations, 'select_relations')
    prefetch_relations, _ = filter_relations(prefetch_relations, 'prefetch_relations')

    if not instance.pk:
        # if this instance isn't saved, we can't fetch anything more
        return

    if not select_relations and not prefetch_relations:
        # nothing to look up
        return

    # select prefetch paths for efficiency
    for relation in prefetch_relations:
        relation_parts = relation.split('__')
        if len(relation_parts) > 1:
            select_relations.append('__'.join(relation_parts[:-1]))
            select_field_names.append(relation_parts[0])

    # fetch a new instance with select_related and prefetch_related
    instance_class = instance._meta.concrete_model
    query = instance_class.objects.only(*select_field_names)
    if select_relations:
        query = query.select_related(*select_relations)
    if prefetch_relations:
        query = query.prefetch_related(*prefetch_relations)
    new_instance = query.get(pk=instance.pk)

    # copy over select_related fields
    for field_name in select_field_names:
        try:
            setattr(instance, field_name, getattr(new_instance, field_name))
        except ObjectDoesNotExist:
            pass  # empty one-to-one field -- just leave it empty

    # copy over prefetch_relations caches into appropriate models
    if prefetch_relations:
        for relation in prefetch_relations:
            # find sub-instance if relation includes __
            sub_instance = instance
            sub_new_instance = new_instance
            relation_parts = relation.split('__')
            relation_path, sub_field_name = relation_parts[:-1], relation_parts[-1]
            for field_name in relation_path:
                sub_instance = getattr(sub_instance, field_name)
                sub_new_instance = getattr(sub_new_instance, field_name)

            # copy cache
            if not hasattr(sub_instance, '_prefetched_objects_cache'):
                sub_instance._prefetched_objects_cache = {}
            sub_instance._prefetched_objects_cache[sub_field_name] = sub_new_instance._prefetched_objects_cache[sub_field_name]


class TransactionTimestampDateTimeField(models.DateTimeField):
    """ Postgres timestamp field that defaults to current_timestamp, the timestamp at the start of the transaction """
    def db_type(self, connection):
        return 'timestamptz DEFAULT current_timestamp'


class SmallForeignKey(models.ForeignKey):
    """
        Foreign keys are usually the same size as the related column. This forces the foreign key to be a smallint instead.
    """
    def db_type(self, connection):
        return 'smallint'


class AutoSlugMixin:
    """
        Mixin for models that set the .slug field on first save.

        Slug can be set in two ways: either manually or automatically.

        Manually:

            case_metadata.save(slug_base="Some Citation")

        Automatically, given that Jurisdiction.get_slug() returns self.name:

            Jurisdiction(name='Massachusetts').save()
    """

    def save(self, *args, slug_base=None, **kwargs):

        # if slug is explicitly provided or blank, keep trying to save until we find a unique slug:
        if slug_base or not self.slug:

            # start with explicit slug_base, or value of self.slug_source:
            slug_base = slugify(slug_base or self.get_slug())

            # try up to 1000 times to save with given slug, adding a number to the slug each time:
            for count in range(1000):
                slug = slug_base
                if count:
                    slug += "-%s" % count
                self.slug = slug
                try:
                    with transaction_safe_exceptions(using='capdb'):
                        return super(AutoSlugMixin, self).save(*args, **kwargs)
                except IntegrityError as e:
                    if 'Key (slug)' not in e.args[0]:
                        raise

            raise Exception(
                "Unable to find unique slug for %s %s, slug_base %s" % (self.__class__.__name__, self.pk, slug_base))

        # normal save without slug modification:
        else:
            return super(AutoSlugMixin, self).save(*args, **kwargs)

    def get_slug(self):
        raise NotImplementedError(
            "Either define a get_slug() method for %s, or pass slug_base to save()." % self.__class__.__name__)


class CachedLookupMixin:
    """
        Mixin for models that have a small number of items that get queried over and over but rarely change.
    """

    # Store all objects from the database here:
    _cached_objects = None

    # Store objects indexed by a given set of keys here. For example,
    #   _lookup_tables[(name, jurisdiction_id)] = {('Foo', 7): obj}
    # This is populated on demand the first time a particular combination of keys is queried.
    _lookup_tables = {}

    def _value_for_keys(self, keys):
        """
            Helper function for get_from_cache.
            Given a list of items like ('name', 'abbreviation'), return (self.name, self.abbreviation).
        """
        return tuple(getattr(self, key) for key in keys)

    @classmethod
    def get_from_cache(cls, **kwargs):
        """
            Get a single item like `Court.get_from_cache(name='Foo', jurisdiction_id=7)`.
            Database will be hit only if that item isn't already in the thread-local cache.
            Entire cache is pre-filled on first call.
        """

        # prefill cache if necessary:
        if cls._cached_objects is None:
            cls._cached_objects = list(cls.objects.all())

        # get sorted list of keys and values to fetch requested object from cache:
        sorted_pairs = sorted(kwargs.items(), key=lambda i: i[0])
        keys = tuple(s[0] for s in sorted_pairs)
        value = tuple(s[1] for s in sorted_pairs)

        # prefill lookup table for this combination of keys, if necessary:
        if keys not in cls._lookup_tables:
            cls._lookup_tables[keys] = {obj._value_for_keys(keys): obj for obj in cls._cached_objects}

        # attempt to return item from cache:
        if value in cls._lookup_tables[keys]:
            return cls._lookup_tables[keys][value]

        # if not in cache, attempt to fetch item from DB (raises cls.DoesNotExist if not found).
        # wrap in transaction_safe_exceptions so callers can catch the DoesNotExist if they want.
        with transaction_safe_exceptions(using='capdb'):
            obj = cls.objects.get(**kwargs)

        # update cache with newly found obj:
        cls._cached_objects.append(obj)
        for k, v in cls._lookup_tables.items():
            v[obj._value_for_keys(k)] = obj

        return obj

    @classmethod
    def reset_cache(cls):
        cls._cached_objects = None
        cls._lookup_tables = {}


### Helpers for XML handling ###

class XMLField(models.TextField):
    """ Column type for Postgres XML columns. """

    def db_type(self, connection):
        return 'xml'

    def from_db_value(self, value, *args, **kwargs):
        """ Make sure that XML returned from postgres includes XML declaration. """
        if value and not value.startswith('<?'):
            return "<?xml version='1.0' encoding='utf-8'?>\n" + value
        return value


class XMLQuerySet(models.QuerySet):
    """ Query methods for BaseXMLModel. """

    def defer_xml(self):
        """
            Defer orig_xml field.

            Note: It might be a good idea to defer this field by default, if and when https://github.com/django/django/pull/9309 lands.
            I played around with adding .defer('orig_xml') to the default queryset, but it broke the refresh_from_db() method --
            seems better to wait until that's an official Django feature.
        """
        return self.defer('orig_xml')


class BaseXMLModel(models.Model):
    """ Base class for models that store XML documents. """
    orig_xml = XMLField()
    md5 = models.CharField(max_length=255, unique=True)
    size = models.IntegerField(blank=True, null=True)

    objects = XMLQuerySet.as_manager()
    tracker = None  # should be set as tracker = FieldTracker() by subclasses

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # no need to save if nothing changed
        if not (set(self.tracker.changed()) - {'sys_period'}):
            return

        # update md5
        if self.tracker.has_changed('orig_xml'):
            if not self.md5 or not self.tracker.has_changed('md5'):
                self.md5 = self.get_md5()
            if not self.tracker.has_changed('size'):
                self.size = self.get_size()

        # Django 2.0 doesn't save byte strings correctly -- make sure we save str()
        if self.orig_xml:
            self.orig_xml = force_str(self.orig_xml)

        return super().save(*args, **kwargs)

    def get_md5(self):
        m = hashlib.md5()
        m.update(force_bytes(self.orig_xml))
        return m.hexdigest()

    def get_size(self):
        return len(force_bytes(self.orig_xml))

    def update_related_sums(self, short_id, new_checksum, new_size):
        parsed_xml = self.get_parsed_xml()
        self.update_related_sums_in_parsed_xml(parsed_xml, short_id, new_checksum, new_size)
        self.orig_xml = serialize_xml(parsed_xml)

    def update_related_sums_in_parsed_xml(self, parsed_xml, short_id, new_checksum, new_size):
        file_el = parsed_xml('mets|file[ID="{}"]'.format(short_id))
        file_el.attr["CHECKSUM"] = new_checksum
        file_el.attr["SIZE"] = str(new_size)

    def xml_modified(self):
        """ Return True if orig_xml was previously saved to the database and is now different. """
        return (
            self.tracker.has_changed('orig_xml') and
            self.pk is not None and
            self.tracker.previous('orig_xml') and
            force_str(self.orig_xml) != self.tracker.previous('orig_xml')
        )

    def get_parsed_xml(self):
        return parse_xml(self.orig_xml)


### models ###


class TrackingToolUser(models.Model):
    """
    These are tracking tool users - they are separate from Capstone users.
    """
    privilege_level = models.CharField(max_length=3, choices=choices('0', '1', '5', '10', '15'),
                                       help_text="The lower the value, the higher the privilege level.")
    email = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self):
        return self.email


class BookRequest(models.Model):
    """
    These were automated emails created in a Tracking Tool interface
    which were sent to the Harvard Depository. They contained a list
    of bar codes, and sometimes, preferred delivery dates and other
    information. Sometimes, when a request was sent manually, a dummy
    request was created in the tracking tool interface for consistency.
    """
    updated_by = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    recipients = models.CharField(max_length=512, blank=True, null=True, help_text="Email recipients")
    from_field = models.CharField(db_column='from', max_length=128, blank=True,
                                  null=True)  # Field renamed because it was a Python reserved word.
    mail_body = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    send_date = models.DateField(blank=True, null=True, help_text="Future date on which to send the request")
    sent_at = models.DateTimeField(blank=True, null=True, help_text="Date which it was actually sent")
    label = models.CharField(max_length=32, blank=True, null=True,
                             help_text="So the user can disambiguate between reqs")
    subject = models.CharField(max_length=512, blank=True, null=True, help_text="Email subject")
    delivery_date = models.DateField(blank=True, null=True, help_text="Requested date of delivery")

    def __str__(self):
        return self.label


class ProcessStep(models.Model):
    """
    For each step in the digitization process, there was an associated
    'process step.' These were recorded in TrackingToolLog.
    """
    PROCESS_STEP_CHOICES = (
        ('Prec', 'received'),
        ('Pana', 'analyzed'),
        ('Ppre', 'prepped'),
        ('Pbat', 'batched'),
        ('Psca', 'scanned'),
        ('Pss1', 'stored, awaiting Meyer'),
        ('Phsc', 'returned to HSC'),
        ('Dqac', 'imaging QA completed'),
        ('Dred', 'redacted'),
        ('Ddep', 'deposited'),
        ('Ding', 'ingested'),
        ('Dqas', 'QA Skipped'),
        ('Preq', 'requested'),
        ('Psea', 'Vacuum Sealed'),
        ('Prqu', 'queued'),
        ('Pnrc', 'not received'),
        ('Dx2v', 'xfer to vendor'),
        ('Phrs', 'holding record suppresse'),
        ('Defv', 'recEvalFilesFromVencor'),
        ('Ppro', 'profiling'),
        ('Pprc', 'profiling complete'),
        ('Pcon', 'conserved'),
        ('Pwor', 'Packaged with Original'),
        ('Pcons', 'Conservation completed'),
        ('Dire', 'Innodata rework'),
        ('Ddup', 'Moved to Dup Bucket'),
        ('Pos', 'Out of Scope'),
        ('Pugv', 'Underground Vaults'),
        ('PdisLewis', 'Moved to Lewis'),
        ('Pmey', 'Meyer pickup'),
        ('Pacm', 'Sent to Acme'),
        ('Pres', 'Reshelved in Langdell'),
        ('Dclr', 'Cleared for Delivery'),
        ('Drcs', 'Received Shared'),
        ('Drcp', 'Received Private'),
        ('Pret', 'Returned to Lender')
    )

    step = models.CharField(unique=True, max_length=255, choices=PROCESS_STEP_CHOICES, primary_key=True,
                            help_text="The process step 'id'")
    label = models.CharField(max_length=24, blank=True, null=True, help_text="Label to use in lists/log views")
    prerequisites = models.CharField(max_length=1024, blank=True, null=True,
                                     help_text="Other psteps which must be completed first")
    description = models.CharField(max_length=256)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self):
        return "%s - %s" % (self.step, self.label)


class Jurisdiction(CachedLookupMixin, AutoSlugMixin, models.Model):
    name = models.CharField(max_length=100, blank=True, db_index=True)
    name_long = models.CharField(max_length=100, blank=True, db_index=True)
    slug = models.SlugField(unique=True, max_length=255)
    whitelisted = models.BooleanField(default=False)

    def __str__(self):
        return self.name_long

    def save(self, *args, **kwargs):
        # set name_long based on name
        if self.name and not self.name_long:
            self.name_long = jurisdiction_translation_long_name.get(self.name, self.name)

        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']

    def get_slug(self):
        return self.name

    @property
    def case_exports(self):
        return CaseExport.objects.filter(filter_type='jurisdiction', filter_id=self.pk)

    def get_absolute_url(self):
        return reverse('jurisdiction-detail', args=[self.slug], scheme="https")

class Reporter(models.Model):
    jurisdictions = models.ManyToManyField(Jurisdiction)
    full_name = models.CharField(max_length=1024, db_index=True)
    short_name = models.CharField(max_length=64)
    short_name_slug = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    start_year = models.IntegerField(blank=True, null=True, help_text="First year of cases for this reporter")
    end_year = models.IntegerField(blank=True, null=True, help_text="Last year of cases for this reporter")
    analyst_start_year = models.IntegerField(blank=True, null=True, help_text="Initial start year added by analyst.")
    analyst_end_year = models.IntegerField(blank=True, null=True, help_text="Initial end year added by analyst.")
    volume_count = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    hollis = ArrayField(models.CharField(max_length=9), blank=True,
                        help_text="This is going to replace the Hollis model")
    is_nominative = models.BooleanField(default=False)
    nominative_for = models.ForeignKey("Reporter", on_delete=models.DO_NOTHING, related_name='nominative_reporters', blank=True, null=True)

    history = TemporalHistoricalRecords()
    objects = TemporalQuerySet.as_manager()

    def __str__(self):
        return "%s: %s %s-%s" % (self.short_name, self.full_name, self.start_year or '', self.end_year or '')

    class Meta:
        ordering = ['full_name']

    def save(self, *args, **kwargs):
        if not self.short_name_slug:
            self.short_name_slug = slugify(self.short_name)
        return super().save(*args, **kwargs)

    @property
    def case_exports(self):
        return CaseExport.objects.filter(filter_type='reporter', filter_id=self.pk)

    def get_absolute_url(self):
        return reverse('reporter-detail', args=[self.id], scheme="https")


class VolumeMetadata(models.Model):
    barcode = models.CharField(unique=True, max_length=64, primary_key=True)

    reporter = models.ForeignKey(Reporter, on_delete=models.DO_NOTHING, related_name='volumes')
    volume_number = models.CharField(max_length=64, blank=True, null=True)
    volume_number_slug = models.CharField(max_length=64, blank=True, null=True)
    nominative_reporter = models.ForeignKey(Reporter, on_delete=models.DO_NOTHING, related_name='nominative_volumes', blank=True, null=True)
    nominative_volume_number = models.CharField(max_length=1024, blank=True, null=True)

    hollis_number = models.CharField(max_length=9, null=True, help_text="Identifier in the Harvard cataloging system, HOLLIS")
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)
    nominative_name = models.CharField(max_length=1024, blank=True, null=True)
    series_volume_number = models.CharField(max_length=1024, blank=True, null=True)
    spine_start_year = models.IntegerField(blank=True, null=True)
    spine_end_year = models.IntegerField(blank=True, null=True)
    start_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    page_start_year = models.IntegerField(blank=True, null=True)
    page_end_year = models.IntegerField(blank=True, null=True)
    contributing_library = models.CharField(max_length=256, blank=True, null=True,
                                            help_text="Several volumes didn't come from our collection")
    rare = models.BooleanField(default=False)
    hsc_review = models.CharField(max_length=9, blank=True, null=True,
                                  choices=choices('No', 'Complete', 'Yes', 'Reclassed'),
                                  help_text="Historical and Special Collections Review")
    needs_repair = models.CharField(max_length=9, blank=True, null=True, choices=choices('No', 'Complete', 'Yes'))
    missing_text_pages = models.TextField(blank=True, null=True, help_text="Pages damaged enough to have lost text.")
    created_by = models.ForeignKey(TrackingToolUser, blank=True, null=True, on_delete=models.DO_NOTHING)
    bibliographic_review = models.CharField(max_length=7, blank=True, null=True,
                                            choices=choices('No', 'Complete', 'Yes'))
    analyst_page_count = models.IntegerField(blank=True, null=True,
                                             help_text="The page number of the last numbered page in the book")
    legacy_duplicate = models.BooleanField(default=False, help_text="From tracking tool; we believe this indicates there is another volume with same hollis_number and volume_number")
    duplicate = models.BooleanField(default=False, help_text="True if there is another volume with same cases")
    duplicate_of = models.ForeignKey("VolumeMetadata", blank=True, null=True, related_name="duplicates", on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    replaced_pages = models.CharField(max_length=1024, blank=True, null=True,
                                      help_text="List of pages that were replaced")
    has_marginalia = models.BooleanField(default=False)
    publication_city = models.CharField(max_length=1024, blank=True, null=True)
    title = models.CharField(max_length=1024, blank=True, null=True)
    hand_feed = models.BooleanField(default=False,
                                    help_text="Instructions for operator, not whether or not it happened")
    image_count = models.IntegerField(blank=True, null=True,
                                      help_text="Count of images recieved from scanner")  # image_count?
    request = models.ForeignKey(BookRequest, blank=True, null=True, on_delete=models.SET_NULL)
    publisher_deleted_pages = models.BooleanField(default=False, help_text="")  # rename?
    notes = models.CharField(max_length=512, blank=True, null=True)
    original_barcode = models.CharField(max_length=64, blank=True, null=True, help_text="")
    scope_reason = models.CharField(max_length=16, blank=True, null=True,
                                    choices=choices('Damaged', 'Not Official', 'Duplicate', 'No Cases'),
                                    help_text="The reason something would be out_of_scope")
    out_of_scope = models.BooleanField(default=False)
    meyer_box_barcode = models.CharField(max_length=32, blank=True, null=True, help_text="The Meyer box barcode")
    uv_box_barcode = models.CharField(max_length=32, blank=True, null=True,
                                      help_text="The Underground Vaults box barcode")
    meyer_ky_truck = models.CharField(max_length=32, blank=True, null=True,
                                      help_text="The Meyer truck to Kentucky this book was shipped on")
    meyer_pallet = models.CharField(max_length=32, blank=True, null=True,
                                    help_text="The pallet Meyer stored the book on")

    ingest_status = models.CharField(max_length=10, default="to_ingest",
                                     choices=choices('to_ingest', 'ingested', 'error', 'skip'))
    ingest_errors = JSONField(blank=True, null=True)
    xml_checksums_need_update = models.BooleanField(default=False,
                                                    help_text="Whether checksums in volume_xml match current values in "
                                                               "related case_xml and page_xml data.")
    pdf_file = models.FileField(blank=True, storage=download_files_storage, help_text="Exported volume PDF")

    # values extracted from VolumeXML
    xml_start_year = models.IntegerField(blank=True, null=True)
    xml_end_year = models.IntegerField(blank=True, null=True)
    xml_publication_year = models.IntegerField(blank=True, null=True)
    xml_publisher = models.CharField(max_length=255, blank=True, null=True)
    xml_publication_city = models.CharField(max_length=1024, blank=True, null=True)
    xml_volume_number = models.CharField(max_length=64, blank=True, null=True)
    # just extract this and keep it here for now -- we can use it to check the reporter= field later:
    xml_reporter_short_name = models.CharField(max_length=255, blank=True, null=True)
    xml_reporter_full_name = models.CharField(max_length=255, blank=True, null=True)
    xml_metadata = JSONField(blank=True, null=True)

    last_es_index = models.DateTimeField(blank=True, null=True, help_text="Last time cases for this volume were successfully indexed by ElasticSearch")

    task_statuses = JSONField(default=dict, help_text="Date and results of tasks run for this volume")

    tracker = FieldTracker()
    history = TemporalHistoricalRecords()
    objects = TemporalQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "Volumes"

    def __str__(self):
        return self.barcode

    def set_xml_checksums_need_update(self, value=True):
        self.xml_checksums_need_update = value
        self.save(update_fields=['xml_checksums_need_update'])

    def get_absolute_url(self):
        return reverse('volumemetadata-detail', args=[self.pk], scheme="https")

    def set_duplicate(self, is_duplicate, duplicate_of=None):
        """
            Update this volume to reflect that it is or is not a duplicate of another volume.
            Update volume.case_metadatas.duplicate and .in_scope to match.
        """
        with transaction.atomic(using='capdb'):
            self.duplicate = is_duplicate
            self.duplicate_of = duplicate_of
            self.save()
            self.case_metadatas.update(duplicate=is_duplicate)
            self.case_metadatas.update_in_scope()

    def set_reporter(self, reporter):
        """
            Update this volume's reporter.
            Update volume.case_metadatas.reporter to match.
        """
        with transaction.atomic(using='capdb'):
            self.reporter = reporter
            self.save()
            self.case_metadatas.update(reporter=reporter)

    def update_volume_number_slug(self):
        self.volume_number_slug = slugify(self.volume_number)

    def save(self, *args, update_volume_number_slug = True, **kwargs):
        if update_volume_number_slug:
            self.update_volume_number_slug()
        super().save(*args, **kwargs)

class TrackingToolLog(models.Model):
    volume = models.ForeignKey(VolumeMetadata, related_name="tracking_tool_logs", on_delete=models.DO_NOTHING)
    entry_text = models.CharField(max_length=128, blank=True,
                                  help_text="Text log entry. Primarily used when pstep isn't set.")
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(TrackingToolUser, related_name="tracking_tool_logs", on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    pstep = models.ForeignKey(ProcessStep, blank=True, null=True, help_text="A significant event in production",
                              related_name="tracking_tool_logs", on_delete=models.SET_NULL)
    exception = models.BooleanField(
        help_text="Nothing to do with software exceptions - more like a UPS delivery 'exception'")
    warning = models.BooleanField(help_text="Something that's a bit off, but not necessarily indicative of a problem")
    version_string = models.CharField(max_length=32, blank=True, null=True,
                                      help_text="'YYYY_DD_MM_hh.mm.ss' Appended to s3 dir to distinguish versions")

    def __str__(self):
        return "%s %s" % (self.pstep, self.entry_text)

    class Meta:
        ordering = ['created_at']


class VolumeXML(BaseXMLModel):
    metadata = models.OneToOneField(VolumeMetadata, related_name='volume_xml', on_delete=models.DO_NOTHING)
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    tracker = FieldTracker()
    history = TemporalHistoricalRecords()
    objects = TemporalQuerySet.as_manager()

    def __str__(self):
        return self.metadata_id

    @transaction.atomic(using='capdb')
    def save(self, update_related=True, *args, **kwargs):

        if (self.tracker.has_changed('orig_xml') and update_related) or self.metadata is None:
            self.update_metadata()

        super().save(*args, **kwargs)

    def update_metadata(self):
        """
            Update related VolumeMetadata object based on updated xml.
        """
        parsed_xml = parse_xml(self.orig_xml)

        if self.metadata is None:
            self.metadata = VolumeMetadata()
        metadata = self.metadata

        metadata.xml_start_year = parsed_xml('volume|voldate > volume|start').text() or None
        if metadata.xml_start_year:
            metadata.xml_start_year = int(metadata.xml_start_year)
        metadata.xml_end_year = parsed_xml('volume|voldate > volume|end').text() or None
        if metadata.xml_end_year:
            metadata.xml_end_year = int(metadata.xml_end_year)
        metadata.xml_publication_year = parsed_xml('volume|publicationdate').text() or None
        if metadata.xml_publication_year:
            metadata.xml_publication_year = int(metadata.xml_publication_year)
        metadata.xml_publisher = parsed_xml('volume|publisher').text() or None
        metadata.xml_publication_city = parsed_xml('volume|publisher').attr.place or None
        metadata.xml_volume_number = parsed_xml('volume|reporter').attr.volnumber or None
        metadata.xml_reporter_short_name = parsed_xml('volume|reporter').attr.abbreviation or None
        metadata.xml_reporter_full_name = parsed_xml('volume|reporter').text() or None

        if metadata.reporter_id is None:
            try:
                metadata.reporter = Reporter.objects.get(short_name=metadata.xml_reporter_short_name)
            except Reporter.DoesNotExist:
                raise Exception("Cannot Find Reporter with Short Name: {} in {}. "
                                "There are {} reporters in the database.".format(
                    metadata.xml_reporter_short_name, self.s3_key, Reporter.objects.count()))
            except Reporter.MultipleObjectsReturned:
                raise Exception("Ambiguous Short Reporter Name: {} in {}".format(
                    metadata.xml_reporter_short_name, self.s3_key))

        if metadata.barcode is None or metadata.barcode is '':
            metadata.barcode = self.s3_key.split('/')[0].split('_redacted')[0]
        if metadata.volume_number is None:
            metadata.volume_number = metadata.xml_volume_number
        if metadata.publisher is None:
            metadata.publisher = metadata.xml_publisher
        if metadata.publication_year is None:
            metadata.publication_year = metadata.xml_publication_year
        if metadata.start_year is None:
            metadata.start_year = metadata.xml_start_year
        if metadata.end_year is None:
            metadata.end_year = metadata.xml_end_year
        if metadata.image_count is None:
            metadata.publication_city = metadata.xml_publication_city

        if metadata.tracker.changed():
            metadata.save()
            self.metadata_id = metadata.pk

    def update_checksums(self):
        """
            Update the size and md5 values in this volume based on the current case_xmls and page_xmls.
            Mark self.metadata.xml_checksums_need_update = False.
        """

        # Build dictionary mapping short IDs to new (md5, size).
        # E.g. {"alto_00009_1": ("bfbd53dc...", 116476)}
        replacements = {}
        for item in self.page_xmls.defer('orig_xml'):
            replacements[item.short_id] = (item.md5, item.size)
        for item in self.case_xmls.defer('orig_xml').select_related('metadata'):
            replacements[item.short_id] = (item.md5, item.size)

        # Below we find all <file> tags with short_ids in the replacements dict, and replace their checksum and size fields.
        # Example file tag:
        #   <file ID="alto_00009_1" MIMETYPE="text/xml" CHECKSUM="bfbd53d..." CHECKSUMTYPE="MD5" SIZE="116476">

        # regex to match file tags
        file_tag_re = r'(<file ID="(%s)" MIMETYPE="text/xml" CHECKSUM=")[^"]+(" CHECKSUMTYPE="MD5" SIZE=")\d+' % '|'.join(replacements.keys())

        # replacement function looks up new values from replacements dict
        def format_file_tag(m):
            new_md5, new_size = replacements[m.group(2)]
            return "%s%s%s%s" % (m.group(1), new_md5, m.group(3), new_size)

        # apply replacements
        self.orig_xml = re.sub(file_tag_re, format_file_tag, self.orig_xml)

        # save results
        self.save()
        self.metadata.set_xml_checksums_need_update(False)


class Court(CachedLookupMixin, AutoSlugMixin, models.Model):
    name = models.CharField(max_length=255, db_index=True)
    name_abbreviation = models.CharField(max_length=100, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='courts',
                                     on_delete=models.SET_NULL)
    slug = models.SlugField(unique=True, max_length=255, blank=False)

    def __str__(self):
        return self.slug

    class Meta:
        ordering = ['name']

    def get_slug(self):
        return self.name_abbreviation or self.name

    def get_absolute_url(self):
        return reverse('court-detail', args=[self.pk], scheme="https")


class CaseMetadataQuerySet(TemporalQuerySet):
    def in_scope(self):
        """
            Return cases accessible from API
        """
        return self.filter(in_scope=True)

    def update_in_scope(self):
        return self.update(in_scope=Q(duplicative=False, duplicate=False) & ~Q(jurisdiction_id=None) & ~Q(court_id=None))


class CaseMetadata(models.Model):
    case_id = models.CharField(max_length=64, unique=True)
    frontend_url = models.CharField(max_length=255, null=True, blank=True)
    first_page = models.CharField(max_length=255, null=True, blank=True, help_text='Label of first page')
    last_page = models.CharField(max_length=255, null=True, blank=True, help_text='Label of first page')
    first_page_order = models.SmallIntegerField(null=True, blank=True, help_text='1-based page order of first page')
    last_page_order = models.SmallIntegerField(null=True, blank=True, help_text='1-based page order of last page')
    publication_status = models.CharField(max_length=255, null=True, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='case_metadatas',
                                     on_delete=models.SET_NULL)
    judges = JSONField(null=True, blank=True)
    parties = JSONField(null=True, blank=True)
    opinions = JSONField(null=True, blank=True)
    attorneys = JSONField(null=True, blank=True)

    docket_number = models.CharField(max_length=20000, blank=True)
    docket_numbers = JSONField(null=True, blank=True)
    decision_date = models.DateField(null=True, blank=True)
    decision_date_original = models.CharField(max_length=100, blank=True)
    argument_date_original = models.CharField(max_length=100, blank=True, null=True)
    court = models.ForeignKey('Court', null=True, related_name='case_metadatas', on_delete=models.SET_NULL)
    district_name = models.CharField(max_length=255, null=True, blank=True)
    district_abbreviation = models.CharField(max_length=255, null=True, blank=True)
    name = models.TextField(blank=True)
    name_abbreviation = models.CharField(max_length=1024, blank=True, db_index=True)
    volume = models.ForeignKey('VolumeMetadata', related_name='case_metadatas',
                               on_delete=models.DO_NOTHING)
    reporter = models.ForeignKey('Reporter', related_name='case_metadatas',
                                 on_delete=models.DO_NOTHING)
    date_added = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    duplicative = models.BooleanField(default=False, help_text="True if case was not processed because it is an unofficial case in a regional reporter")
    duplicate = models.BooleanField(default=False, help_text="True if case was processed but is a duplicate of another preferred case")
    duplicate_of = models.ForeignKey("CaseMetadata", blank=True, null=True, on_delete=models.SET_NULL, related_name="duplicates")
    withdrawn = models.BooleanField(default=False, help_text="True if case was withdrawn by the court")
    replaced_by = models.ForeignKey("CaseMetadata", blank=True, null=True, on_delete=models.SET_NULL, related_name="replaced")
    no_index = models.BooleanField(default=False, help_text="True if case should not be included in google index")
    no_index_notes = models.TextField(blank=True, null=True, help_text="Reason no_index is true")

    no_index_elided = JSONField(blank=True, null=True, help_text="Elided text will be shown on click. Example: {\"Text to elide (must be exact match)\": \"Extra text that's currently not used. Can be left as empty string.\"}")
    no_index_redacted = JSONField(blank=True, null=True, help_text="Redacted text will be hidden from view and replaced with key's value specified above. Example: {\"Text to redact (must be exact match)\": \"Text to replace redacted text.\"}")

    in_scope = models.BooleanField(default=True, help_text="True if case should be included in public data")
    initial_metadata_synced = models.BooleanField(default=False)
    robots_txt_until = models.DateTimeField(blank=True, null=True, help_text="Frontend URL for this case will be included in robots.txt until this date")

    custom_footer_message = models.TextField(blank=True, null=True, help_text="If not provided, custom footer will be filled with default text if elisions or redactions exist")

    objects = CaseMetadataQuerySet.as_manager()
    history = TemporalHistoricalRecords()

    def __str__(self):
        return self.case_id

    class Meta:
        indexes = [
            # partial index for robots_txt_until cases
            models.Index(name='idx_robots_txt_until', fields=('robots_txt_until',), condition=~Q(robots_txt_until=None)),
        ]

    def save(self, *args, **kwargs):
        if self.in_scope != self.get_in_scope():
            self.in_scope = not self.in_scope
        if settings.MAINTAIN_ELASTICSEARCH_INDEX and not getattr(kwargs, 'no_reindex', False) and self.pk and hasattr(self, 'body_cache'):
            self.update_search_index()
        super().save(*args, **kwargs)

    def full_cite(self):
        return "%s, %s%s" % (
            self.name_abbreviation,
            ", ".join(cite.cite for cite in Citation.sorted_by_type(self.citations.all()) if cite.type != 'vendor'),
            " (%s)" % self.decision_date.year if self.decision_date else ""
        )

    def get_absolute_url(self):
        return reverse('cases-detail', kwargs={'id': self.id}, scheme="https")

    @classmethod
    def update_frontend_urls(cls, cite_strs, update_elasticsearch=True, batch_size=100):
        """
            Update frontend_url for all cases affected by a group of citation updates.
            cite_strs should include both old and new citations. For example, if a case was corrected from
            "124 Foo 456" to "123 Foo 456", cite_strs should include both strings.
        """
        # handle sets/iters
        if type(cite_strs) != list:
            cite_strs = list(cite_strs)

        for i in range(0, len(cite_strs), batch_size):
            cites = Citation.objects.filter(cite__in=cite_strs[i:i+batch_size], type='official').order_by('cite').select_related('case__volume', 'case__reporter')
            if update_elasticsearch:
                cites = cites.select_related('case__court', 'case__jurisdiction', 'case__body_cache')
            cite_groups = itertools.groupby(cites, key=lambda c: c.cite)
            to_update = []

            # go through each group of cases that share the same official cite, and set their frontend url.
            # if more than one case in a group, then include disambiguation in the url.
            for k, cite_group in cite_groups:
                cite_group = list(cite_group)
                disambiguate = len(cite_group) > 1
                for cite in cite_group:
                    case = cite.case
                    new_frontend_url = case.get_frontend_url(cite, include_host=False, disambiguate=disambiguate)
                    if new_frontend_url != case.frontend_url:
                        case.frontend_url = new_frontend_url
                        to_update.append(case)

            if to_update:
                cls.objects.bulk_update(to_update, ['frontend_url'])
                if update_elasticsearch:
                    cls.reindex_cases(to_update)

    @classmethod
    def reindex_cases(cls, cases):
        from capapi.documents import CaseDocument  # avoid circular import
        CaseDocument().update(cases)

    def get_frontend_url(self, cite=None, disambiguate=False, include_host=True):
        """
            Return cite.case.law cite for this case, like /series/volnum/pagenum/.
            If disambiguate is true, return /series/volnum/pagenum/id/.
        """
        cite = cite or self.citations.first()

        # try to match "(volnumber) (Series) (pagenumber)"
        m = re.match(r'^(\S+(?: Suppl\.| 1/2)?)\s+([A-Z].+?)\s+(\S+)$', cite.cite)

        if not m:
            # if cite doesn't match the expected format, always disambiguate so URL resolution doesn't depend on cite value
            disambiguate = True
            # try to match "(year)-(series)-(case index)", e.g. "2017-Ohio-5699" and "2015-NMCA-053"
            m = re.match(r'(\S+)-(.+?)-(\S+)$', cite.cite)

        # TODO: final fallback value is wrong, because first_page is the physical page count and not the page label
        # after token streams are in, we should be able to retrieve the actual page label instead
        volume_number, rep_short_nm, fp = m.groups() if m else [self.volume.volume_number, self.reporter.short_name, self.first_page]

        args = [slugify(rep_short_nm), slugify(volume_number), fp] + ([self.id] if disambiguate else [])
        url = reverse('citation', args=args, host='cite')
        if not include_host:
            # strip https://cite.case.law prefix so stored value can be moved between servers
            url = '/'+url.split('/',3)[3]
        return url

    def get_full_frontend_url(self):
        return reverse('cite_home').rstrip('/') + self.frontend_url

    def get_pdf_url(self):
        pdf_name = re.sub(r'[\\/:*?"<>|]', '_', self.full_cite()) + ".pdf"
        return reverse('case_pdf', [self.pk, pdf_name])

    def withdraw(self, new_value=True, replaced_by=None):
        """ Mark this case as withdrawn by the court, and optionally replaced by a new case. """
        self.withdrawn = new_value
        self.replaced_by = replaced_by
        self.save()
        self.sync_case_body_cache()

    def update_search_index(self):
        from capapi.documents import CaseDocument  # local to avoid circular import
        CaseDocument().update(self)

    def get_hydrated_structure(self):
        """
            Return structure for this case with all references to page blocks replaced by the actual block contents.
            This is useful for diagnosing rendering errors.
        """
        structure = self.structure
        blocks_by_id = PageStructure.blocks_by_id(structure.pages.all())
        renderer = render_case.VolumeRenderer(blocks_by_id, {}, {})
        return renderer.hydrate_opinions(structure.opinions, blocks_by_id)

    def sync_case_body_cache(self, blocks_by_id=None, fonts_by_id=None, labels_by_block_id=None, rerender=True):
        """
            Update self.body_cache with new values based on the current value of self.structure.
            blocks_by_id and fonts_by_id can be provided for efficiency if updating a bunch of cases from the same volume.
        """

        # if rerender is false, just regenerate json and text attributes from existing html
        if not rerender:
            try:
                body_cache = self.body_cache
            except CaseBodyCache.DoesNotExist:
                return
            json, text = self.get_json_from_html(body_cache.html)
            CaseBodyCache.objects.filter(id=body_cache.id).update(json=json, text=text)
            return

        structure = self.structure
        if not blocks_by_id or not labels_by_block_id:
            pages = list(structure.pages.all())
        blocks_by_id = blocks_by_id or PageStructure.blocks_by_id(pages)
        fonts_by_id = fonts_by_id or CaseFont.fonts_by_id(blocks_by_id)
        labels_by_block_id = labels_by_block_id or PageStructure.labels_by_block_id(pages)

        renderer = render_case.VolumeRenderer(blocks_by_id, fonts_by_id, labels_by_block_id)
        html = renderer.render_html(self)
        xml = renderer.render_xml(self)
        json, text = self.get_json_from_html(html)

        ## save
        params = {
            'text': text,
            'html': html,
            'xml': xml,
            'json': json,
        }
        # use this approach, instead of update_or_create, to reduce sql traffic:
        #   - avoid causing a select (if the body_cache has already been populated with select_related)
        #   - avoid hydrating the params via save(), if they were loaded with defer()
        try:
            body_cache = self.body_cache
        except CaseBodyCache.DoesNotExist:
            CaseBodyCache(metadata=self, **params).save()
        else:
            CaseBodyCache.objects.filter(id=body_cache.id).update(**params)

        if settings.MAINTAIN_ELASTICSEARCH_INDEX:
            self.update_search_index()

    def get_json_from_html(self, html):
        casebody_pq = PyQuery(html)
        casebody_pq.remove('.page-label,.footnotemark,.bracketnum')  # remove page numbers and references from text/json

        # extract each opinion into a dictionary
        opinions = []
        for opinion in casebody_pq.items('.opinion'):
            opinions.append({
                'type': opinion.attr['data-type'],
                'author': opinion('.author').text() or None,
                'text': opinion.text(),
            })
        json = {
            'head_matter': casebody_pq('.head-matter').text(),
            'judges': [judge.text() for judge in casebody_pq('.judges').items()],
            'attorneys': [attorney.text() for attorney in casebody_pq('.attorneys').items()],
            'parties': [party.text() for party in casebody_pq('.parties').items()],
            'opinions': opinions,
            'corrections': casebody_pq('.corrections').text(),
        }
        text = "\n".join([json['head_matter']] + [o['text'] for o in json['opinions']] + [json['corrections']])
        return json, text

    def sync_from_initial_metadata(self, force=False):
        """
            Update metadata values for this case based on the value of self.initial_metadata.
            We will only do this the first time, unless force=True, to avoid stepping on values that are later updated
            directly.
        """
        if self.initial_metadata_synced and not force:
            return
        self.initial_metadata_synced = True
        data = self.initial_metadata.metadata

        # set up data
        duplicative_case = data['duplicative']

        self.duplicative = duplicative_case
        self.first_page = data["first_page"]
        self.last_page = data["last_page"]

        if not duplicative_case:
            self.name = data["name"]
            self.name_abbreviation = data["name_abbreviation"]
            self.publication_status = data["status"]
            self.decision_date_original = data["decision_date"]
            self.decision_date = parse_decision_date(data["decision_date"])
            self.argument_date_original = data.get("argument_date")
            if data["docket_numbers"]:
                self.docket_number = data["docket_numbers"][0]
            self.docket_numbers = data["docket_numbers"]
            if data.get("district"):
                self.district_name = data["district"]["name"]
                self.district_abbreviation = data["district"]["abbreviation"]

            # apply fixes from scripts.fix_court_tag
            court = data["court"]
            if court.get('jurisdiction') and court.get('name') and court.get('abbreviation'):
                court['jurisdiction'], court['name'], court['abbreviation'] = fix_court_tag(court['jurisdiction'], court['name'], court['abbreviation'])

            # set jurisdiction
            try:
                if self.volume.barcode in special_jurisdiction_cases:
                    jurisdiction_name = special_jurisdiction_cases[self.volume.barcode]
                else:
                    jurisdiction_name = jurisdiction_translation[court["jurisdiction"]]
                self.jurisdiction = Jurisdiction.get_from_cache(name=jurisdiction_name)
            except KeyError:
                # just mark these as None -- they require manual cleanup
                self.jurisdiction = None

            # set or create court
            # we look up court by name, name_abbreviation, and jurisdiction
            court_kwargs = {obj_key:court[data_key] for obj_key, data_key in (('name', 'name'), ('name_abbreviation', 'abbreviation')) if data_key in court}
            if self.jurisdiction and court_kwargs:
                court_kwargs["jurisdiction_id"] = self.jurisdiction_id
                try:
                    court = Court.get_from_cache(**court_kwargs)
                except Court.DoesNotExist:
                    court = Court(**court_kwargs)
                    court.save()
                self.court = court

        self.save()

        ### Handle citations

        # set up a fake cite for duplicate cases
        if duplicative_case:
            # only makes sense to create a citation if we have a label for the first page
            first_page = self.structure.pages.order_by('order').first()
            if first_page and first_page.label:
                citations = [{
                    'category': 'official',
                    'type': 'bluebook',
                    'text': "{} {} {}".format(self.volume.volume_number, self.reporter.short_name, first_page.label),
                    'duplicative': True,
                }]
            else:
                citations = []
        else:
            citations = data['citations']

        # create each citation
        self.citations.all().delete()
        if citations:
            Citation.objects.bulk_create(Citation(
                cite=citation['text'],
                normalized_cite=Citation.normalize_cite(citation['text']),
                type=citation['category'],
                category=citation['type'],
                duplicative=citation.get('duplicative', False),
                case=self,
            ) for citation in citations)

    def get_in_scope(self):
        """ Return correct value for .in_scope """
        return not self.duplicative and not self.duplicate and bool(self.jurisdiction_id) and bool(self.court_id)

    def retrieve_and_store_images(self):
        """Get all <img> tags in casebody, store file images in db"""
        casebody = self.body_cache.html
        casebody = BeautifulSoup(casebody, 'html.parser')
        imgs = casebody.findAll('img')
        known_hashes = {c.hash for c in self.caseimages.all()}

        for idx, img in enumerate(imgs):
            frmt, data = img['src'].split(';base64,')
            ext = frmt.split('/')[-1]
            data_decoded = base64.b64decode(data)
            h = hashlib.new(name="md5", data=data_decoded).hexdigest()

            # handle existing images
            if h in known_hashes:
                CaseImage.objects.filter(case=self, hash=h).update(position_index=idx)
                known_hashes.remove(h)

            # handle new images
            else:
                width, height = struct.unpack('>ii', data_decoded[16:24])
                CaseImage(
                    case=self,
                    hash=h,
                    data=ContentFile(data_decoded, name='%s-%s.%s' % (self.id, h, ext)),
                    height=height,
                    width=width,
                    position_index=idx,
                ).save()

        # handle deleted images
        if known_hashes:
            CaseImage.objects.filter(case=self, hash__in=known_hashes).delete()

    def get_pdf(self):
        """
            Return PDF for this case from volume PDF. `fitz` is the PyMuPDF library.
        """
        if not self.volume.pdf_file:
            raise ValueError("Cannot get case PDF for volume with no PDF")
        doc = fitz.open(self.volume.pdf_file.path)
        doc.select(range(self.first_page_order-1, self.last_page_order))
        return doc.write(garbage=2)


class CaseXML(BaseXMLModel):
    metadata = models.OneToOneField(CaseMetadata, blank=True, null=True, related_name='case_xml',
                                    on_delete=models.SET_NULL)
    volume = models.ForeignKey(VolumeXML, related_name='case_xmls',
                               on_delete=models.DO_NOTHING)
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    tracker = FieldTracker()
    history = TemporalHistoricalRecords()
    objects = TemporalQuerySet.as_manager()

    @transaction.atomic(using='capdb')
    def save(self, update_related=True, *args, **kwargs):
        # allow disabling of create_or_update_metadata for testing
        create_or_update_metadata = kwargs.pop('create_or_update_metadata', True)

        if self.tracker.has_changed('orig_xml'):
            # prefetch data needed by create_or_update_metadata() and process_updated_xml()
            fetch_relations(self,
                select_relations=['volume__metadata__reporter'],
                prefetch_relations=['metadata__citations'])

            # Create or update related CaseMetadata object
            if create_or_update_metadata:
                self.create_or_update_metadata(update_existing=True, save_self=False)

            # Update related VolumeXML and PageXML contents
            if self.xml_modified() and update_related:
                self.metadata.volume.set_xml_checksums_need_update()
                self.process_updated_xml()

        # save that ish.
        super(CaseXML, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.pk)

    def process_updated_xml(self):
        """
            Update related PageXML and VolumeXML records based on updates to this record's XML.
            We don't yet support adding or removing words from the case body.

            This function should only be called if orig_xml has changed from a previously saved version,
            and should only need to be called from save().
        """

        # If the case is duplicative, nothing needs to be done
        if self.metadata.duplicative:
            return

        # parse objects and get the xml tree objects
        parsed_original_case = parse_xml(self.tracker.previous('orig_xml'))
        parsed_updated_case = parse_xml(self.orig_xml)
        original_casebody_tree = parsed_original_case("casebody|casebody")[0]
        updated_casebody_tree = parsed_updated_case("casebody|casebody")[0]

        # if there are no changes inside casebody, nothing needs to be done
        if etree.tostring(original_casebody_tree) == etree.tostring(updated_casebody_tree):
            return

        updated_tree = parsed_updated_case.root
        original_tree = parsed_original_case.root

        # get a list of casebody elements and make sure there's no additions or deletions
        original_casebody_xpaths = set([original_tree.getelementpath(element) for element in original_casebody_tree])
        updated_casebody_xpaths = set([updated_tree.getelementpath(element) for element in updated_casebody_tree])

        removed = original_casebody_xpaths - updated_casebody_xpaths
        added = updated_casebody_xpaths - original_casebody_xpaths

        if len(added) > len(removed):
            raise Exception("No current support for adding casebody elements")
        elif len(added) < len(removed):
            raise Exception("No current support for removing casebody elements")
        elif len(added) > 0 or len(removed) > 0:
            # if we have the same number of added and removed, see
            # if they have the same parent in the xpath, which means
            # they're probably renamed elements rather than additions/deletions
            removed_base_xpaths = []
            for xpath in removed:
                base_path = xpath.rsplit('}', 1)[0] + '}'
                removed_base_xpaths.append(base_path)

            added_base_xpaths = []
            for xpath in added:
                base_path = xpath.rsplit('}', 1)[0] + '}'
                added_base_xpaths.append(base_path)

            # get the difference
            added_base_path_diff = set(added_base_xpaths) - set(removed_base_xpaths)
            removed_base_path_diff = set(removed_base_xpaths) - set(added_base_xpaths)

            if len(added) > len(removed) or len(added_base_path_diff) > 0:
                raise Exception("No current support for adding casebody elements")
            if len(removed) > len(added) or len(removed_base_path_diff) > 0:
                raise Exception("No current support for removing casebody elements")

        # get the alto files associated with the case in the DB
        alto_files = {alto.short_id: (alto, parse_xml(alto.orig_xml)) for alto in self.pages.all()}
        modified_alto_files = set()

        # check to see if any elements in the casebody have been updated so we can update the ALTO
        # since the tree structures match, we can just iterate over the tree elements and compare values
        for original_element in original_casebody_tree.iter():
            xpath = original_tree.getpath(original_element)
            updated_element = updated_tree.xpath(xpath)[0]

            # in the alto_connections dict is a map between the pgmap value, such as '17' and the
            # FILEID value, such as alto_0008_0
            alto_connections = {}
            alto_element_references = parsed_original_case(
                'mets|area[BEGIN="{}"]'.format(original_element.get('id'))).parent().nextAll('mets|fptr')
            for area in alto_element_references('mets|area'):
                pgmap = area.get('BEGIN').split(".")[0].split("_")[1]
                alto_connections[pgmap] = area.get('FILEID')

            # frequently, case text elements span pages. This gets the alto pages referred
            # to by the element's pagemap attribute, and returns the alto_id of the page
            if "pgmap" in original_element.keys() and ' ' in original_element.get("pgmap"):
                element_pages = [alto_connections[page.split('(')[0]] for page in
                                 original_element.get("pgmap").split(" ")]
            elif "pgmap" in original_element.keys():
                element_pages = [alto_connections[original_element.get("pgmap")]]

            # check for a modified tag name
            if original_element.tag != updated_element.tag:
                # go through each alto file that refers to the tag and update the reference
                for short_id in element_pages:
                    alto, parsed_alto = alto_files[short_id]
                    structure_tag = parsed_alto(
                        'alto|StructureTag[ID="{}"]'.format(original_element.get('id')))
                    if structure_tag is not None:
                        structure_tag.attr["LABEL"] = updated_element.tag.rsplit('}', 1)[1]
                        modified_alto_files.add(alto)

            # check for modified element text
            if original_element.text != updated_element.text:
                # we haven't devised a strategy for dealing with this yet
                if len(updated_element.text.split(" ")) != len(original_element.text.split(" ")):
                    raise Exception("No current support for adding or removing case text")

                # Case text elements can include text from multiple alto pages. To compare them you need
                # to get all of the elements from all of the pages and compare them to a list of words
                # from the case text.
                wordcount = 0
                # loop through each referenced alto file
                for short_id in element_pages:
                    alto, parsed_alto = alto_files[short_id]
                    text_block = parsed_alto(
                        'alto|TextBlock[TAGREFS="{}"]'.format(original_element.get('id')))
                    words = text_block("alto|String")

                    updated_element_split = updated_element.text.split(" ")
                    original_element_split = original_element.text.split(" ")

                    # loop through each word in the ALTO text block
                    for word in words:
                        updated_word = updated_element_split[wordcount]
                        original_word = original_element_split[wordcount]
                        assert original_word == word.get("CONTENT")
                        if updated_word != original_word:
                            modified_alto_files.add(alto)
                            # update ALTO & set the character confidence and word confidence to 100%
                            word.set("WC", "1.00")
                            word.set("CC", "0")
                            word.set("CONTENT", updated_element.text.split(" ")[wordcount])
                        wordcount += 1

        # update and save the modified altos, and update the md5/size in the case
        for alto in modified_alto_files:
            alto.orig_xml = serialize_xml(alto_files[alto.short_id][1])
            alto.save(save_case=False, save_volume=False)
            self.update_related_sums_in_parsed_xml(parsed_updated_case, alto.short_id, alto.md5, alto.size)

        self.orig_xml = serialize_xml(parsed_updated_case)

    def create_or_update_metadata(self, update_existing=True, save_self=True):
        """
            creates or updates CaseMetadata object
            - if we want to skip over updating existing case metadata objects
            method returns out.
            - otherwise, create or overwrite properties on related metadata object
        """

        # get or create case.metadata
        if self.metadata_id:
            if not update_existing:
                return
            case_metadata = self.metadata
            metadata_created = False
        else:
            case_metadata = CaseMetadata()
            metadata_created = True

        # set up data
        data, parsed = get_case_metadata(force_str(self.orig_xml))
        duplicative_case = data['duplicative']
        volume_metadata = self.volume.metadata
        reporter = volume_metadata.reporter

        # set case_metadata attributes
        case_metadata.reporter = reporter
        case_metadata.volume = volume_metadata
        case_metadata.duplicative = duplicative_case
        case_metadata.first_page = data["first_page"]
        case_metadata.last_page = data["last_page"]
        case_metadata.case_id = data["case_id"]

        if not duplicative_case:
            case_metadata.name = data["name"]
            case_metadata.name_abbreviation = data["name_abbreviation"]
            case_metadata.decision_date_original = data["decision_date_original"]
            case_metadata.decision_date = data["decision_date"]
            case_metadata.docket_number = data["docket_number"]

            case_metadata.judges = data["judges"]
            case_metadata.parties = data["parties"]
            case_metadata.opinions = data["opinions"]
            case_metadata.attorneys = data["attorneys"]

            # set jurisdiction
            try:
                if data['volume_barcode'] in special_jurisdiction_cases:
                    jurisdiction_name = special_jurisdiction_cases[data["volume_barcode"]]
                else:
                    jurisdiction_name = jurisdiction_translation[data["jurisdiction"]]
                case_metadata.jurisdiction = Jurisdiction.get_from_cache(name=jurisdiction_name)
            except KeyError:
                # just mark these as None -- they require manual cleanup
                case_metadata.jurisdiction = None

            # set or create court
            # we look up court by name, name_abbreviation, and jurisdiction
            court_kwargs = {k: v for k, v in data["court"].items() if v}
            if court_kwargs and case_metadata.jurisdiction:
                court_kwargs['jurisdiction_id'] = case_metadata.jurisdiction.id
                try:
                    court = Court.get_from_cache(**court_kwargs)
                except Court.DoesNotExist:
                    court = Court(**court_kwargs)
                    court.save()
                case_metadata.court = court

        case_metadata.save()

        ### Handle citations

        # fetch any existing cites from the database
        existing_cites = {} if metadata_created else {cite.cite: cite for cite in self.metadata.citations.all()}

        # set up a fake cite for duplicate cases
        if duplicative_case:
            citations = [{
                "citation_type": "official",
                "citation_text": "{} {} {}".format(volume_metadata.volume_number, reporter.short_name, data["first_page"]),
                "is_duplicative": True,
            }]
        else:
            citations = data['citations']

        # update or create each citation
        for citation in citations:
            if citation['citation_text'] in existing_cites:
                cite = existing_cites.pop(citation['citation_text'])
                cite.cite = citation['citation_text']
                cite.type = citation['citation_type']
                cite.duplicative = citation['is_duplicative']
            else:
                cite = Citation(
                    cite=citation['citation_text'],
                    type=citation['citation_type'],
                    duplicative=citation['is_duplicative'],
                    case=case_metadata,
                )
            if cite.tracker.changed():
                cite.save()

        # clean up unused existing cites
        Citation.objects.filter(pk__in=[cite.pk for cite in existing_cites.values()]).delete()

        # create link between casexml and metadata
        if metadata_created:
            self.metadata = case_metadata
            if save_self:
                self.save(update_fields=['metadata'])

    @property
    def short_id(self):
        """ ID of this case as referred to by volume xml file. """
        return short_id_from_s3_key(self.s3_key)

    def extract_casebody(self, reorder_head_matter=True):
        """
            Return pyquery casebody element for this case.
            By default, this strips soft hyphens and reorders head matter to match the print order.
        """
        # strip soft hyphens from line endings
        text = self.orig_xml.replace(u'\xad', '')
        parsed_xml = parse_xml(text)
        if reorder_head_matter:
            self.reorder_head_matter(parsed_xml)
        return parsed_xml('casebody|casebody')

    @staticmethod
    def reorder_head_matter(parsed_xml):
        """
            Reorder head matter (elements inside <casebody>, before the first <opinion>) to match the reading order
            from the printed page. We can get reading order by sorting by the ID of the associated ALTO elements,
            which is stored in the <div TYPE="blocks"> section of the case XML.
        """
        # Head matter elements look like:
        #     <casebody ...>
        #         <foo id="b17-10">...</foo>
        # First remove all of those elements, up to the first element without an ID, and store them in removed_els by ID:
        casebody = parsed_xml('casebody|casebody')
        removed_els = []
        for el in casebody.children().items():
            if not el.attr('id'):
                break
            removed_els.append(el.remove())
        if not removed_els:
            return

        # Alto associations look like:
        #   <div TYPE="blocks">
        #     <div TYPE="element">
        #         <fptr><area BEGIN="b15-4" .../></fptr>
        #         <fptr><seq><area BEGIN="BL_15.2" .../></seq></fptr>
        #     </div>
        # Build a dictionary of ID to ALTO order for sorting, e.g. {'b15-4': (15, 2),)}
        # ALTO blocks have IDs like "BL_<page number>.<block number>", so extract the two numbers to sort numerically.
        # Skip elements inside footnotes. We can more often do the correct thing by attaching entities to the closest
        # non-footnote element -- though this will do the wrong thing when entities were extracted from footnotes in
        # the first place.
        def sortable_id(alto_id):
            parts = alto_id.split('_')[1].split('.')
            return (int(parts[0]), int(parts[1]))
        ignore_ids = {el.attr.id for el in casebody('casebody|footnote [id],casebody|correction').items()}
        id_to_alto_order = {}
        for xref_el in parsed_xml('mets|div[TYPE="blocks"] > mets|div[TYPE="element"]').items():
            par_el, blocks_el = xref_el('mets|fptr').items()
            par_id = par_el('mets|area').attr.BEGIN
            if par_id in ignore_ids:
                continue
            alto_ids = [el.attrib['BEGIN'] for el in blocks_el('mets|area')]
            # for an empty paragraph with contents redacted, there's no alto_id
            if alto_ids:
                alto_ids = sorted(sortable_id(alto_id) for alto_id in alto_ids)
                id_to_alto_order[par_id] = alto_ids[0]

        # Split remove_els into head_els and opinion_els, based on whether or not they come before the first
        # element in the first opinion:
        removed_els.sort(key=lambda el: id_to_alto_order.get(el.attr.id, (math.inf,)))
        first_opinion_el_id = next((el.attr.id for el in parsed_xml('casebody|opinion').children().items() if el.attr.id in id_to_alto_order), None)
        head_els = []
        opinion_els = []
        if first_opinion_el_id:
            for el in removed_els:
                if el.attr.id not in id_to_alto_order or id_to_alto_order[el.attr.id] < id_to_alto_order[first_opinion_el_id]:
                    head_els.append(el)
                else:
                    opinion_els.append(el)
        else:
            head_els = removed_els

        # Add all head_els back to the <casebody>
        for el in reversed(head_els):
            casebody.prepend(el)

        # Add all opinion_els back, immediately after whatever existing element they come after in sorted order
        if opinion_els:
            sorted_ids = sorted(id_to_alto_order.keys(), key=lambda key: id_to_alto_order[key])
            previous_id_lookup = dict(zip(sorted_ids, [None]+sorted_ids))
            for el in opinion_els:
                previous_el = casebody('[id="%s"]' % previous_id_lookup[el.attr.id])
                if not previous_el.length:
                    # this shouldn't happen, so throw an exception here to make sure we can't lose elements
                    raise Exception("Unable to locate previous element %s for element %s" % (previous_id_lookup[el.attr.id], el.attr.id))
                casebody('[id="%s"]' % previous_id_lookup[el.attr.id]).after(el)

class Citation(models.Model):
    citation_types = ("official", "nominative", "parallel", "vendor")  # citation types in sort order
    citation_type_sort_order = {citation_type: i for i, citation_type in enumerate(citation_types)}

    type = models.CharField(max_length=100, choices=list(zip(citation_types, citation_types)))
    category = models.CharField(max_length=100, blank=True, null=True)  # this field and "type" are reversed from the values in CaseXML -- possibly should be switched back?
    cite = models.CharField(max_length=10000, db_index=True)
    duplicative = models.BooleanField(default=False)
    normalized_cite = models.SlugField(max_length=10000, null=True, db_index=True)
    case = models.ForeignKey('CaseMetadata', related_name='citations', null=True, on_delete=models.SET_NULL)

    tracker = FieldTracker()
    history = TemporalHistoricalRecords()
    objects = TemporalQuerySet.as_manager()

    def __str__(self):
        return str(self.cite)

    class Meta:
        ordering = ['type']  # so official will come back before parallel

    def save(self, *args, **kwargs):
        if self.tracker.has_changed('cite'):
            self.normalized_cite = self.normalize_cite(self.cite)
        super(Citation, self).save(*args, **kwargs)

    @staticmethod
    def normalize_cite(cite):
        return re.sub(r'[^0-9a-z]', '', cite.lower())

    def page_number(self):
        return self.cite.rsplit(' ', 1)[-1]

    @classmethod
    def sorted_by_type(cls, cites):
        return sorted(cites, key=lambda c: cls.citation_type_sort_order[c.type])

class PageXML(BaseXMLModel):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    volume = models.ForeignKey(VolumeXML, related_name='page_xmls',
                               on_delete=models.DO_NOTHING)
    cases = models.ManyToManyField(CaseXML, related_name='pages')
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    tracker = FieldTracker()
    history = TemporalHistoricalRecords()
    objects = TemporalQuerySet.as_manager()

    class Meta:
        ordering = ['barcode']

    @transaction.atomic(using='capdb')
    def save(self, force_insert=False, force_update=False, save_case=True, save_volume=True, *args, **kwargs):
        if self.xml_modified():
            if save_volume:
                self.volume.metadata.set_xml_checksums_need_update()
            if save_case:
                for case in self.cases.all():
                    case.update_related_sums(self.short_id, self.get_md5(), str(self.get_size()))
                    case.save()
        super(PageXML, self).save(force_insert, force_update, *args, **kwargs)

    def __str__(self):
        return self.barcode

    @property
    def short_id(self):
        """ ID of this page as referred to by volume xml file. """
        return short_id_from_s3_key(self.s3_key)


class ExtractedCitation(models.Model):
    cite_original = models.CharField(max_length=10000, db_index=True)
    cited_by = models.ForeignKey(CaseMetadata, related_name='extractedcitations', on_delete=models.DO_NOTHING)
    reporter_name_original = models.CharField(max_length=200)
    volume_number_original = models.CharField(max_length=64, blank=True, null=True)
    page_number_original = models.SmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.cite_original


class DataMigration(models.Model):
    data_migration_timestamp = models.DateTimeField(auto_now_add=True)
    transaction_timestamp = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10,
                              choices=(("applied", "applied"), ("pending", "pending"), ("error", "error")))
    traceback = models.TextField(blank=True, null=True)
    author = models.CharField(max_length=255)
    initiator = models.CharField(max_length=255)
    alto_xml_changed = JSONField()
    volume_xml_changed = JSONField()
    case_xml_changed = JSONField()
    alto_xml_rollback = JSONField()
    volume_xml_rollback = JSONField()
    case_xml_rollback = JSONField()


class SlowQuery(models.Model):
    query = models.TextField()
    label = models.CharField(max_length=255, blank=True, null=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen']
        verbose_name_plural = "Slow queries"

    def __str__(self):
        return self.label or self.query


class CaseExportQuerySet(models.QuerySet):
    """ Query methods for BaseXMLModel. """

    def exclude_old(self):
        """
            Return only the latest file for each export (based on filter_type, filter_id, body_format)
        """
        return self.extra(where=['id in (SELECT max(id) FROM capdb_caseexport GROUP BY (filter_type, filter_id, body_format))'])

class CaseExport(models.Model):
    file_name = models.CharField(max_length=255)
    file = models.FileField(storage=bulk_export_storage)
    body_format = models.CharField(max_length=10, choices=(('xml','xml'),('text','text')))

    export_date = models.DateTimeField(auto_now_add=True)
    public = models.BooleanField(default=False)

    # do it this way instead of with GenericForeignKey because Django's content_type table is in the other database
    filter_type = models.CharField(max_length=20, choices=(('jurisdiction','jurisdiction'),('reporter','reporter')))
    filter_id = models.PositiveIntegerField(null=True, blank=True)

    objects = CaseExportQuerySet.as_manager()

    _filter_item_lookup = {'jurisdiction': Jurisdiction, 'reporter': Reporter}
    _filter_item_cache = None

    @property
    def filter_item(self):
        """ Return the Jurisdiction or Reporter referred to by filter_type and filter_id. """
        if not self._filter_item_cache:
            self._filter_item_cache = self._filter_item_lookup[self.filter_type].objects.get(pk=self.filter_id)
        return self._filter_item_cache

    @classmethod
    def load_filter_items(cls, instances):
        """
            Set the .filter_item property for a list of instances -- this uses fewer sql queries than calling
            instance.filter_item individually for each instance.
        """
        lookups = {
            filter_type: {item.pk: item for item in model.objects.filter(
                pk__in=[instance.filter_id for instance in instances if instance.filter_type == filter_type])}
            for filter_type, model in cls._filter_item_lookup.items()
        }
        for instance in instances:
            instance._filter_item_cache = lookups[instance.filter_type][instance.filter_id]


class Snippet(models.Model):
    """
        Data snippets for use on the website. It's just a cache for data that is both static enough, and resource-
        intensive enough to generate that periodic updates would suit it best.
    """
    contents = models.TextField(null=False, blank=True, help_text="Contents in string, JSON, etc.")
    label = models.CharField(max_length=24, null=False, unique=True, help_text="Label")
    format = models.CharField(max_length=128, null=False, help_text="Data Format",
                              choices=choices("application/json", "text/tab-separated-values", "text/plain"))

    def __str__(self):
        return self.label


class TarFile(models.Model):
    """
        A captar file that was used for ingest.
    """
    volume = models.OneToOneField(VolumeMetadata, on_delete=models.DO_NOTHING, related_name='tar_file')
    storage_path = models.CharField(max_length=1000)
    hash = models.CharField(max_length=1000)

    def __str__(self):
        return "%s <%s>" % (self.storage_path, self.hash)


class CaseFont(models.Model):
    """
        A distinct font used in one or more alto files.
    """
    family = models.CharField(max_length=100)
    size = models.CharField(max_length=100)
    style = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=100)
    width = models.CharField(max_length=100)

    class Meta:
        unique_together = ('family', 'size', 'style', 'type', 'width')

    def __str__(self):
        return "%s %s %s" % (self.family, self.size, self.style)

    @classmethod
    def fonts_by_id(cls, blocks_by_id):
        font_ids = []
        for block in blocks_by_id.values():
            for token in block.get('tokens', []):
                if type(token) != str and token[0] == 'font':
                    font_ids.append(token[1]['id'])
        return {t.id: t for t in cls.objects.filter(pk__in=font_ids)}


class PageStructure(models.Model):
    """
        Data structure derived from an ALTO file for a page of a volume.
    """
    volume = models.ForeignKey(VolumeMetadata, on_delete=models.DO_NOTHING, related_name='page_structures')
    order = models.SmallIntegerField()
    label = models.CharField(max_length=100, blank=True)

    blocks = JSONField()
    spaces = JSONField(blank=True, null=True)  # probably unnecessary -- in case pages ever have more than one PrintSpace
    font_names = JSONField(blank=True, null=True)  # for mapping font IDs back to style names in alto
    encrypted_strings = models.TextField(blank=True, null=True)
    duplicates = JSONField(blank=True, null=True)  # list of duplicate IDs detected during conversion
    extra_redacted_ids = JSONField(blank=True, null=True)  # list of IDs redacted during conversion

    image_file_name = models.CharField(max_length=100)
    width = models.SmallIntegerField()
    height = models.SmallIntegerField()
    deskew = models.CharField(max_length=1000, blank=True)

    ingest_source = models.ForeignKey(TarFile, on_delete=models.DO_NOTHING)
    ingest_path = models.CharField(max_length=1000)

    def order_to_alto_id(self):
        """ Convert 1 to alto_00001_0, 2 to alto_00001_1, 3 to alto_00002_0, and so on. """
        return 'alto_%05d_%s' % ((self.order+1)//2, (self.order+1)%2)

    @staticmethod
    def blocks_by_id(pages):
        blocks = {}
        for page in pages:
            for block in page.blocks:
                blocks[block['id']] = block
        return blocks

    @staticmethod
    def labels_by_block_id(pages):
        labels = {}
        for page in pages:
            for block in page.blocks:
                labels[block['id']] = page.label
        return labels

    def encrypt(self, key=settings.REDACTION_KEY):
        """
            Encrypt a page dictionary. Example:
            >>> key = b'CGiDpvmQr8NlDnamAhr6Idv8NR+zwpY5i9zEfuWoZSI='
            >>> page = PageStructure(blocks=[ \
                {'format': 'image', 'redacted':True, 'data':'unencrypted'}, \
                {'redacted':True, 'tokens': ['text']}, \
                {'tokens': ['text', ['redact'], 'text', ['/redact']]}, \
                ])
            >>> page.encrypt(key)
            >>> assert page.blocks == [
            ...     {'format': 'image', 'redacted':True, 'data':['enc', {'i':1}]},
            ...     {'redacted':True, 'tokens': [['enc', {'i':0}]]},
            ...     {'tokens': ['text', ['redact'], ['enc', {'i':0}], ['/redact']]},
            ... ]
            >>> assert len(page.encrypted_strings) == 84
            >>> page.decrypt(key)
            >>> assert page.blocks == [
            ...     {'format': 'image', 'data': 'unencrypted', 'redacted': True},
            ...     {'tokens': ['text'], 'redacted': True},
            ...     {'tokens': ['text', ['redact'], 'text', ['/redact']]}
            ... ]
        """
        if self.encrypted_strings:
            raise ValueError("Cannot encrypt page with existing 'encrypted_strings' value.")

        # extract each redacted string and replace it with a reference like ['enc', {'i': 1}]. i value will later become the
        # index into an encrypted array of strings.
        strings = {}
        string_counter = 0
        for block in self.blocks:
            if block.get('format') == 'image':
                if block.get('redacted', False):
                    enc_data = strings[block['data']] = ['enc', {'i': string_counter}]
                    block['data'] = enc_data
                    string_counter += 1
            else:
                all_redacted = block.get('redacted', False)
                redacted_span = False
                tokens = block.get('tokens', [])
                for i in range(len(tokens)):
                    token = tokens[i]
                    if type(token) == str:
                        if all_redacted or redacted_span:
                            if token not in strings:
                                strings[token] = ['enc', {'i': string_counter}]
                                string_counter += 1
                            tokens[i:i + 1] = [strings[token]]
                    elif token[0] == 'redact':
                        redacted_span = True
                    elif token[0] == '/redact':
                        redacted_span = False

        # update references with correct i values
        string_vals = sorted(strings.keys())  # sorted so indexes are stable for testing
        for i, val in enumerate(string_vals):
            strings[val][1]['i'] = i

        # store encrypted array
        box = nacl.secret.SecretBox(force_bytes(key), encoder=nacl.encoding.Base64Encoder)
        self.encrypted_strings = box.encrypt(json.dumps(string_vals).encode('utf8'),
                                             encoder=nacl.encoding.Base64Encoder).decode('utf8')

    def decrypt(self, key=settings.REDACTION_KEY):
        """
            Decrypt a page dictionary. Performs the reverse transformation to the example for encrypt().
        """
        # decrypt stored strings
        box = nacl.secret.SecretBox(force_bytes(key), encoder=nacl.encoding.Base64Encoder)
        strings = json.loads(
            box.decrypt(self.encrypted_strings.encode('utf8'), encoder=nacl.encoding.Base64Encoder).decode('utf8'))

        # replace tokens like ['enc', {'i': 1}] with ith entry from strings array
        for block in self.blocks:
            if block.get('format') == 'image':
                if block.get('redacted', False):
                    block['data'] = strings[block['data'][1]['i']]
            else:
                tokens = block.get('tokens', [])
                for i in range(len(tokens)):
                    token = tokens[i]
                    if type(token) != str and token[0] == 'enc':
                        tokens[i:i + 1] = [strings[token[1]['i']]]


class CaseStructure(models.Model):
    """
        Structure of a case, based on references to PageStructure.
    """
    metadata = models.OneToOneField(CaseMetadata, on_delete=models.DO_NOTHING, related_name='structure')
    pages = models.ManyToManyField(PageStructure, related_name='cases')
    opinions = JSONField()

    ingest_source = models.ForeignKey(TarFile, on_delete=models.DO_NOTHING)
    ingest_path = models.CharField(max_length=1000)


class CaseInitialMetadata(models.Model):
    """
        Initial metadata for case, provided by Innodata.
    """
    case = models.OneToOneField(CaseMetadata, on_delete=models.DO_NOTHING, related_name='initial_metadata')
    metadata = JSONField()

    ingest_source = models.ForeignKey(TarFile, on_delete=models.DO_NOTHING)
    ingest_path = models.CharField(max_length=1000)


class CaseBodyCache(models.Model):
    """
    Renditions of a case.
    """
    metadata = models.OneToOneField(CaseMetadata, related_name='body_cache', on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    html = models.TextField(blank=True, null=True)
    xml = models.TextField(blank=True, null=True)
    json = JSONField(blank=True, null=True)


class EditLog(models.Model):
    """
        Record a set of edits. Simple usage:

            with EditLog(description='message').record():
                volume.save()

        Advanced usage:

            with EditLog(description='message').record(auto_transaction=False) as edit:
                if things_are_bad:
                    raise edit.Cancel
                for i in stuff:
                    with edit.atomic():
                        i.save()
    """

    timestamp = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField(blank=True, null=True)
    description = models.TextField()

    class Meta:
        ordering = ['-timestamp']

    @contextmanager
    def record(self, auto_transaction=True):
        """
            Context manager to record an EditLog along with any transactions run inside it.
        """
        self.save()
        try:
            if auto_transaction:
                with self.atomic():
                    yield self
            else:
                yield self
        except self.Cancel:
            self.delete()
        except Exception:
            if auto_transaction:
                self.delete()
            raise

    class Cancel(Exception):
        """ Raise this to delete the current log, if auto_transaction=False. """
        pass

    @contextmanager
    def atomic(self, using='capdb', savepoint=True):
        """ Wrapper to open and record transactions within the current log, if auto_transaction=False. """
        with transaction.atomic(using, savepoint):
            self.mark_transaction()
            yield

    def mark_transaction(self):
        EditLogTransaction(edit=self).save()


class EditLogTransaction(models.Model):
    """
        Record of a single transaction that was used while recording an EditLog. Can be linked up to history tables
        by comparing timestamp to sys_period.
    """
    edit = models.ForeignKey(EditLog, on_delete=models.CASCADE, related_name='transactions')
    timestamp = TransactionTimestampDateTimeField()

    def _do_insert(self, manager, using, fields, update_pk, raw):
        """
            filter out timestamp from inserts, because it has a database default Django doesn't know about
        """
        timestamp_field = self._meta.get_field('timestamp')
        fields = tuple(f for f in fields if f != timestamp_field)
        return super()._do_insert(manager, using, fields, update_pk, raw)


class CaseImage(models.Model):
    case = models.ForeignKey('CaseMetadata', related_name='caseimages', on_delete=models.DO_NOTHING)
    position_index = models.IntegerField(null=True)
    data = models.FileField(storage=case_image_storage)
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
    hash = models.CharField(max_length=1000)

    def __str__(self):
        return "%s %s" % (self.position_index, self.hash)

    class Meta:
        unique_together = ['case', 'hash']

