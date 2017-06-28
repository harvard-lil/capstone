from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models

### helpers ###

def choices(*args):
    """ Simple helper to create choices=(('Foo','Foo'),('Bar','Bar'))"""
    return zip(args, args)

### custom column types ###

class XMLField(models.TextField):
    """
        Column type for Postgres XML columns.
    """
    def db_type(self, connection):
        return 'xml'

### models ###

class TrackingToolUser(models.Model):
    """
    These are tracking tool users– they are separate from Capstone users.
    """
    privilege_level = models.CharField(max_length=3, choices=choices('0', '1', '5', '10', '15'), help_text="The lower the value, the higher the privilege level.")
    email = models.CharField(max_length=32)
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

class Reporter(models.Model):
    jurisdiction = models.CharField(max_length=64, blank=True, null=True)
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

class VolumeMetadata(models.Model):
    barcode = models.CharField(unique=True, max_length=64, primary_key=True)
    hollis_number = models.CharField(max_length=9, help_text="Identifier in the Harvard catalogging system, HOLLIS")
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
    rare = models.BooleanField()
    hsc_review = models.CharField(max_length=9, blank=True, null=True, choices=choices('No', 'Complete', 'Yes', 'Reclassed'), help_text="Historical and Special Collections Review")
    needs_repair = models.CharField(max_length=9, blank=True, null=True, choices=choices('No', 'Complete', 'Yes'))
    missing_text_pages = models.TextField(blank=True, null=True, help_text="Pages damaged enough to have lost text.")
    created_by = models.ForeignKey(TrackingToolUser)
    bibliographic_review = models.CharField(max_length=7, blank=True, null=True, choices=choices('No', 'Complete', 'Yes'))
    analyst_page_count = models.IntegerField(blank=True, null=True, help_text="The page number of the last numbered page in the book")
    duplicate = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    replaced_pages = models.CharField(max_length=1024, blank=True, null=True, help_text="List of pages that were replaced")
    has_marginalia = models.BooleanField()  
    publication_city = models.CharField(max_length=1024, blank=True, null=True)
    title = models.CharField(max_length=1024, blank=True, null=True)
    hand_feed = models.BooleanField(help_text="Instructions for operator, not whether or not it happened")
    image_count = models.IntegerField(blank=True, null=True, help_text="Count of images recieved from scanner")  # image_count?
    request = models.ForeignKey(BookRequest, blank=True, null=True)
    publisher_deleted_pages = models.BooleanField(help_text="")  # rename?
    notes = models.CharField(max_length=512, blank=True, null=True)
    original_barcode = models.CharField(max_length=64, blank=True, null=True, help_text="")
    scope_reason = models.CharField(max_length=16, blank=True, null=True, choices=choices('Damaged','Not Official','Duplicate','No Cases'), help_text="The reason something would be out_of_scope")
    out_of_scope = models.BooleanField()
    meyer_box_barcode = models.CharField(max_length=32, blank=True, null=True, help_text="The Meyer box barcode")
    uv_box_barcode = models.CharField(max_length=32, blank=True, null=True, help_text="The Underground Vaults box barcode")
    meyer_ky_truck = models.CharField(max_length=32, blank=True, null=True, help_text="The Meyer truck to Kentucky this book was shipped on")
    meyer_pallet = models.CharField(max_length=32, blank=True, null=True, help_text="The pallet Meyer stored the book on")

    class Meta:
        verbose_name_plural = "Volumes"

    def __str__(self):
        return self.barcode


class TrackingToolLog(models.Model):
    volume = models.ForeignKey(VolumeMetadata)
    entry_text = models.CharField(max_length=128, blank=True, help_text="Text log entry. Primarily used when pstep isn't set.")
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(TrackingToolUser)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    pstep = models.ForeignKey(ProcessStep, blank=True, null=True, help_text="A significant event in production")
    exception = models.BooleanField(help_text="Nothing to do with software exceptions– more like a UPS delivery 'exception'")
    warning = models.BooleanField(help_text="Something that's a bit off, but not necessarily indicative of a problem")
    version_string = models.CharField(max_length=32, blank=True, null=True, help_text="'YYYY_DD_MM_hh.mm.ss' Appended to s3 dir to distinguish versions")

    def __str__(self):
        return "%s %s" % (self.pstep, self.entry_text)

class VolumeXML(models.Model):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)  # models.OneToOneField(VolumeMetadata)
    orig_xml = XMLField()

    def __str__(self):
        return self.barcode

class CaseXML(models.Model):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    orig_xml = XMLField()
    volume = models.ForeignKey(VolumeXML)

    def __str__(self):
        return self.barcode

class PageXML(models.Model):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    orig_xml = XMLField()
    volume = models.ForeignKey(VolumeXML)
    cases = models.ManyToManyField(CaseXML, related_name='pages')

    def __str__(self):
        return self.barcode

class DataMigration(models.Model):
    data_migration_timestamp = models.DateTimeField(auto_now_add=True)
    transaction_timestamp = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=(("applied","applied"),("pending","pending"),("error","error")))
    traceback = models.TextField(blank=True, null=True)
    author = models.CharField(max_length=255)
    initiator = models.CharField(max_length=255)
    alto_xml_changed = JSONField()
    volume_xml_changed = JSONField()
    case_xml_changed = JSONField()
    alto_xml_rollback = JSONField()
    volume_xml_rollback = JSONField()
    case_xml_rollback = JSONField()
