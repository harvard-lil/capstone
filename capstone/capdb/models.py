import hashlib
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models

from scripts.process_metadata import get_case_metadata
from .utils import generate_unique_slug
from scripts.helpers import *

### helpers ###

def choices(*args):
    """ Simple helper to create choices=(('Foo','Foo'),('Bar','Bar'))"""
    return zip(args, args)


### Helpers for XML handling ###

class XMLField(models.TextField):
    """ Column type for Postgres XML columns. """
    def db_type(self, connection):
        return 'xml'


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

    objects = XMLQuerySet.as_manager()

    class Meta:
        abstract = True

    def md5(self):
        m = hashlib.md5()
        m.update(self.orig_xml.encode())
        return m.hexdigest()


### models ###


class TrackingToolUser(models.Model):
    """
    These are tracking tool users - they are separate from Capstone users.
    """
    privilege_level = models.CharField(max_length=3, choices=choices('0', '1', '5', '10', '15'), help_text="The lower the value, the higher the privilege level.")
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
    from_field = models.CharField(db_column='from', max_length=128, blank=True, null=True)  # Field renamed because it was a Python reserved word.
    mail_body = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    send_date = models.DateField(blank=True, null=True, help_text="Future date on which to send the request")
    sent_at = models.DateTimeField(blank=True, null=True, help_text="Date which it was actually sent")
    label = models.CharField(max_length=32, blank=True, null=True, help_text="So the user can disambiguate between reqs")
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

    step = models.CharField(unique=True, max_length=255, choices=PROCESS_STEP_CHOICES, primary_key=True, help_text="The process step 'id'")
    label = models.CharField(max_length=24, blank=True, null=True, help_text="Label to use in lists/log views")
    prerequisites = models.CharField(max_length=1024, blank=True, null=True, help_text="Other psteps which must be completed first")
    description = models.CharField(max_length=256)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self):
        return "%s - %s" % (self.step, self.label)


class Jurisdiction(models.Model):
    name = models.CharField(max_length=100, blank=True)
    name_long = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True, max_length=255)
    whitelisted = models.BooleanField(default=False)

    def __str__(self):
        return self.slug

    class Meta:
        ordering = ['name']


class Reporter(models.Model):
    jurisdictions = models.ManyToManyField(Jurisdiction)
    full_name = models.CharField(max_length=1024)
    short_name = models.CharField(max_length=64)
    start_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    volume_count = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    hollis = ArrayField(models.CharField(max_length=9), blank=True, help_text="This is going to replace the Hollis model")

    def __str__(self):
        return "%s: %s %s-%s" % (self.short_name, self.full_name, self.start_year or '', self.end_year or '')

    class Meta:
        ordering = ['full_name']


class VolumeMetadata(models.Model):
    barcode = models.CharField(unique=True, max_length=64, primary_key=True)
    hollis_number = models.CharField(max_length=9, help_text="Identifier in the Harvard cataloging system, HOLLIS")
    volume_number = models.CharField(max_length=64, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)
    reporter = models.ForeignKey(Reporter)
    nominative_volume_number = models.CharField(max_length=1024, blank=True, null=True)
    nominative_name = models.CharField(max_length=1024, blank=True, null=True)
    series_volume_number = models.CharField(max_length=1024, blank=True, null=True)
    spine_start_year = models.IntegerField(blank=True, null=True)
    spine_end_year = models.IntegerField(blank=True, null=True)
    start_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    page_start_year = models.IntegerField(blank=True, null=True)
    page_end_year = models.IntegerField(blank=True, null=True)
    contributing_library = models.CharField(max_length=256, blank=True, null=True, help_text="Several volumes didn't come from our collection")
    rare = models.BooleanField(default=False)
    hsc_review = models.CharField(max_length=9, blank=True, null=True, choices=choices('No', 'Complete', 'Yes', 'Reclassed'), help_text="Historical and Special Collections Review")
    needs_repair = models.CharField(max_length=9, blank=True, null=True, choices=choices('No', 'Complete', 'Yes'))
    missing_text_pages = models.TextField(blank=True, null=True, help_text="Pages damaged enough to have lost text.")
    created_by = models.ForeignKey(TrackingToolUser)
    bibliographic_review = models.CharField(max_length=7, blank=True, null=True, choices=choices('No', 'Complete', 'Yes'))
    analyst_page_count = models.IntegerField(blank=True, null=True, help_text="The page number of the last numbered page in the book")
    duplicate = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    replaced_pages = models.CharField(max_length=1024, blank=True, null=True, help_text="List of pages that were replaced")
    has_marginalia = models.BooleanField(default=False)
    publication_city = models.CharField(max_length=1024, blank=True, null=True)
    title = models.CharField(max_length=1024, blank=True, null=True)
    hand_feed = models.BooleanField(default=False, help_text="Instructions for operator, not whether or not it happened")
    image_count = models.IntegerField(blank=True, null=True, help_text="Count of images recieved from scanner")  # image_count?
    request = models.ForeignKey(BookRequest, blank=True, null=True)
    publisher_deleted_pages = models.BooleanField(default=False, help_text="")  # rename?
    notes = models.CharField(max_length=512, blank=True, null=True)
    original_barcode = models.CharField(max_length=64, blank=True, null=True, help_text="")
    scope_reason = models.CharField(max_length=16, blank=True, null=True, choices=choices('Damaged','Not Official','Duplicate','No Cases'), help_text="The reason something would be out_of_scope")
    out_of_scope = models.BooleanField(default=False)
    meyer_box_barcode = models.CharField(max_length=32, blank=True, null=True, help_text="The Meyer box barcode")
    uv_box_barcode = models.CharField(max_length=32, blank=True, null=True, help_text="The Underground Vaults box barcode")
    meyer_ky_truck = models.CharField(max_length=32, blank=True, null=True, help_text="The Meyer truck to Kentucky this book was shipped on")
    meyer_pallet = models.CharField(max_length=32, blank=True, null=True, help_text="The pallet Meyer stored the book on")

    class Meta:
        verbose_name_plural = "Volumes"

    def __str__(self):
        return self.barcode

    @property
    def volume_xml(self):
        # TODO: Once OneToOneField is set up, this method can be deleted
        return VolumeXML.objects.filter(barcode=self.barcode).first()


class TrackingToolLog(models.Model):
    volume = models.ForeignKey(VolumeMetadata, related_name="tracking_tool_logs")
    entry_text = models.CharField(max_length=128, blank=True, help_text="Text log entry. Primarily used when pstep isn't set.")
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(TrackingToolUser, related_name="tracking_tool_logs")
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    pstep = models.ForeignKey(ProcessStep, blank=True, null=True, help_text="A significant event in production", related_name="tracking_tool_logs")
    exception = models.BooleanField(help_text="Nothing to do with software exceptions - more like a UPS delivery 'exception'")
    warning = models.BooleanField(help_text="Something that's a bit off, but not necessarily indicative of a problem")
    version_string = models.CharField(max_length=32, blank=True, null=True, help_text="'YYYY_DD_MM_hh.mm.ss' Appended to s3 dir to distinguish versions")

    def __str__(self):
        return "%s %s" % (self.pstep, self.entry_text)

    class Meta:
        ordering = ['created_at']


class VolumeXML(BaseXMLModel):
    metadata = models.OneToOneField(VolumeMetadata, related_name='volume_xml')
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    def __str__(self):
        return self.metadata_id


class Court(models.Model):
    name = models.CharField(max_length=255)
    name_abbreviation = models.CharField(max_length=100, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='courts', on_delete=models.SET_NULL)
    slug = models.SlugField(unique=True, max_length=255, blank=False)

    def save(self, *args, **kwargs):
        if not self.id and not self.slug:
            self.slug = generate_unique_slug(self, self.name_abbreviation or self.name)
        super(Court, self).save(*args, **kwargs)

    def __str__(self):
        return self.slug

    class Meta:
        ordering = ['name']


class CaseMetadata(models.Model):
    slug = models.SlugField(max_length=255, unique=True)
    case_id = models.CharField(max_length=64, null=True)
    first_page = models.IntegerField(null=True, blank=True)
    last_page = models.IntegerField(null=True, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='case_metadatas',
                                     on_delete=models.SET_NULL)
    citations = models.ManyToManyField('Citation', related_name='case_metadatas')
    docket_number = models.CharField(max_length=255, blank=True)
    decision_date = models.DateField(null=True, blank=True)
    decision_date_original = models.CharField(max_length=100, blank=True)
    court = models.ForeignKey('Court', null=True, related_name='case_metadatas', on_delete=models.SET_NULL)
    name = models.TextField(blank=True)
    name_abbreviation = models.CharField(max_length=255, blank=True)
    volume = models.ForeignKey('VolumeMetadata', null=True, related_name='case_metadatas',
                                 on_delete=models.SET_NULL)
    reporter = models.ForeignKey('Reporter', null=True, related_name='case_metadatas',
                                 on_delete=models.SET_NULL)
    date_added = models.DateTimeField(null=True, blank=True)
    duplicative = models.BooleanField(default=False)

    def __str__(self):
        return self.slug

    class Meta:
        ordering = ['case_id']

    def save(self, *args, **kwargs):
        # Ordinarily we would set slug here for new objects, but we can't because it's based on self.citations,
        # which is a many-to-many that can't exist until the object is saved.
        super(CaseMetadata, self).save(*args, **kwargs)


class CaseXML(BaseXMLModel):
    metadata = models.OneToOneField(CaseMetadata, blank=True, null=True, related_name='case_xml')
    volume = models.ForeignKey(VolumeXML, related_name='case_xmls')
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    def __str__(self):
        return str(self.pk)

    def create_or_update_metadata(self, update_existing=True):
        """
            creates or updates CaseMetadata object
            - if we want to skip over updating existing case metadata objects
            method returns out.
            - otherwise, create or overwrite properties on related metadata object
        """
        case_metadata = self.metadata
        if case_metadata:
            if not update_existing:
                # if case already exists, return out
                return case_metadata
            metadata_created = False
        else:
            case_metadata = CaseMetadata()
            metadata_created = True

        data = get_case_metadata(self.orig_xml)
        duplicative_case = data['duplicative']

        volume_metadata = self.volume.metadata
        reporter = volume_metadata.reporter

        # we have to create citations first because case slug field relies on citation
        citations = list()

        if not duplicative_case:
            for citation_type, citation_text in data['citations'].items():
                cite, created = Citation.objects.get_or_create(
                    cite=citation_text,
                    type=citation_type,
                    duplicative=False)
                citations.append(cite)
        else:
            cite, created = Citation.objects.get_or_create(
                cite="{} {} {}".format(volume_metadata.volume_number, reporter.short_name, data["first_page"]),
                type="official", duplicative=True)
            citations.append(cite)

        case_metadata.reporter = reporter
        case_metadata.volume = volume_metadata
        case_metadata.duplicative = duplicative_case
        case_metadata.first_page = data["first_page"]
        case_metadata.last_page = data["last_page"]
        case_metadata.case_id = data["case_id"]

        # set slug to official citation, or first citation if there is no official
        citation_to_slugify = next((c for c in citations if c.type == 'official'), citations[0])
        case_metadata.slug = generate_unique_slug(case_metadata, citation_to_slugify.cite)

        # save here so we can add citation relationships before possibly returning
        case_metadata.save()
        # TODO: this may create orphan citations that aren't linked to any case
        case_metadata.citations.set(citations)

        if metadata_created:
            self.metadata = case_metadata
            self.save()

        if duplicative_case:
            return

        case_metadata.name = data["name"]
        case_metadata.name_abbreviation = data["name_abbreviation"]
        case_metadata.decision_date_original = data["decision_date_original"]
        case_metadata.decision_date = data["decision_date"]
        case_metadata.docket_number = data["docket_number"]

        if data['volume_barcode'] in special_jurisdiction_cases:
            case_metadata.jurisdiction = Jurisdiction.objects.get(name=special_jurisdiction_cases[data["volume_barcode"]])
        else:
            case_metadata.jurisdiction = Jurisdiction.objects.get(name=jurisdiction_translation[data["jurisdiction"]])

        court_name = data["court"]["name"]
        court_name_abbreviation = data["court"]["name_abbreviation"]

        if court_name and court_name_abbreviation:
            court, created = Court.objects.get_or_create(
                name=court_name,
                name_abbreviation=court_name_abbreviation)
            case_metadata.court = court

        elif court_name_abbreviation:
            court, created = Court.objects.get_or_create(
                name_abbreviation=court_name_abbreviation)
            case_metadata.court = court

        elif court_name:
            court, created = Court.objects.get_or_create(
                name=court_name)
            case_metadata.court = court

        if case_metadata.court and case_metadata.jurisdiction:
            court.jurisdiction = case_metadata.jurisdiction
            court.save()

        case_metadata.save()

        return case_metadata


class Citation(models.Model):
    type = models.CharField(max_length=100,
                            choices=(("official", "official"), ("parallel", "parallel")))
    cite = models.CharField(max_length=255)
    duplicative = models.BooleanField(default=False)
    slug = models.SlugField(max_length=255, unique=True)

    def save(self, *args, **kwargs):
        if not self.id and not self.slug:
            self.slug = generate_unique_slug(self, self.cite)
        super(Citation, self).save(*args, **kwargs)

    def __str__(self):
        return self.slug


class PageXML(BaseXMLModel):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    volume = models.ForeignKey(VolumeXML, related_name='page_xmls')
    cases = models.ManyToManyField(CaseXML, related_name='pages')
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    def __str__(self):
        return self.barcode


class DataMigration(models.Model):
    data_migration_timestamp = models.DateTimeField(auto_now_add=True)
    transaction_timestamp = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=(("applied", "applied"), ("pending", "pending"), ("error", "error")))
    traceback = models.TextField(blank=True, null=True)
    author = models.CharField(max_length=255)
    initiator = models.CharField(max_length=255)
    alto_xml_changed = JSONField()
    volume_xml_changed = JSONField()
    case_xml_changed = JSONField()
    alto_xml_rollback = JSONField()
    volume_xml_rollback = JSONField()
    case_xml_rollback = JSONField()
