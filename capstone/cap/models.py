from django.contrib.postgres.fields import JSONField
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
    privlevel = models.CharField(max_length=3, choices=choices('0', '1', '5', '10', '15'))  # priv_level?
    email = models.CharField(max_length=320)
    #password = models.CharField(max_length=64)
    active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    remember_token = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.email

class BookRequest(models.Model):
    updated_by = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    recipients = models.CharField(max_length=512, blank=True, null=True)
    from_field = models.CharField(db_column='from', max_length=128, blank=True, null=True)  # Field renamed because it was a Python reserved word.
    mail_body = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    send_date = models.DateField(blank=True, null=True)
    label = models.CharField(max_length=32, blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    subject = models.CharField(max_length=512, blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)

class ProcessStep(models.Model):
    step_id = models.CharField(unique=True, max_length=255, primary_key=True)
    type = models.CharField(max_length=1, blank=True, null=True)
    name = models.CharField(max_length=24, blank=True, null=True)
    prereq = models.CharField(max_length=1024, blank=True, null=True)
    desc = models.CharField(max_length=256)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self):
        return "%s - %s" % (self.step_id, self.name)

class Reporter(models.Model):
    state = models.CharField(max_length=64, blank=True, null=True)
    reporter = models.CharField(max_length=256)  # full_name?
    short = models.CharField(max_length=64)  # short_name?
    start_date = models.IntegerField(blank=True, null=True)  # start_year?
    end_date = models.IntegerField(blank=True, null=True)  # end_year?
    volumes = models.IntegerField(blank=True, null=True)  # volume_count?
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    original_volumes = models.IntegerField(blank=True, null=True)  # original_volume_count?
    original_start_date = models.CharField(max_length=4, blank=True, null=True)  # original_start_year?
    original_end_date = models.CharField(max_length=4, blank=True, null=True)  # original_end_year?
    observed_start_date = models.IntegerField(blank=True, null=True)  # observed_start_year?
    observed_end_date = models.IntegerField(blank=True, null=True)  # observed_end_year?
    observed_volumes = models.IntegerField(blank=True, null=True)  # observed_volume_count?

    def __str__(self):
        return "%s: %s %s-%s" % (self.short, self.reporter, self.start_date or '', self.end_date or '')

class Hollis(models.Model):
    hollis_no = models.CharField(max_length=9, blank=True, null=True)  # hollis_number?
    reporter = models.ForeignKey(Reporter)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Hollis entries"

    def __str__(self):
        return self.hollis_no

class VolumeMetadata(models.Model):
    bar_code = models.CharField(unique=True, max_length=64, primary_key=True)

    # tracking tool fields
    hollis_no = models.CharField(max_length=128)
    volume = models.CharField(max_length=64, blank=True, null=True)  # volume_number?
    publicationdate = models.DateField(blank=True, null=True)  # publication_date?
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publicationyear = models.IntegerField(blank=True, null=True)  # publication_year?
    reporter = models.ForeignKey(Reporter, blank=True, null=True)  # can this really be blank?
    publicationdategranularity = models.CharField(max_length=1, blank=True, null=True)  # publication_date_granularity? unused?
    nom_volume = models.CharField(max_length=1024, blank=True, null=True)  # nominative_volume_number?
    nominative_name = models.CharField(max_length=1024, blank=True, null=True)
    series_volume = models.CharField(max_length=1024, blank=True, null=True)  # series_volume_number?
    spine_start_date = models.IntegerField(blank=True, null=True)  # spine_start_year?
    spine_end_date = models.IntegerField(blank=True, null=True)  # spine_end_year?
    start_date = models.IntegerField(blank=True, null=True)  # start_year?
    end_date = models.IntegerField(blank=True, null=True)  # end_year?
    page_start_date = models.IntegerField(blank=True, null=True)  # page_start_year?
    page_end_date = models.IntegerField(blank=True, null=True)  # page_end_year?
    redaction_profile = models.CharField(max_length=1, blank=True, null=True)  # unused?
    contributing_library = models.CharField(max_length=256, blank=True, null=True)
    rare = models.BooleanField()
    hscrev = models.CharField(max_length=255, blank=True, null=True)
    hsc_accession = models.DateTimeField(blank=True, null=True)
    needs_repair = models.CharField(max_length=255, blank=True, null=True, choices=choices('N', 'C', 'Y'))
    missing_text_pages = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(TrackingToolUser)
    bibrev = models.CharField(max_length=1, blank=True, null=True, choices=choices('N', 'C', 'Y'))
    pages = models.IntegerField(blank=True, null=True)  # page_count?
    dup = models.BooleanField()  # duplicate?
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    replaced_pages = models.CharField(max_length=1024, blank=True, null=True)
    cases = models.IntegerField(blank=True, null=True)  # unused?
    marginalia = models.BooleanField()  # has_marginalia?
    pop = models.CharField(max_length=1024, blank=True, null=True)  # publication_city?
    title = models.CharField(max_length=1024, blank=True, null=True)
    handfeed = models.BooleanField()
    imgct = models.IntegerField(blank=True, null=True)  # image_count?
    hold = models.BooleanField()
    request = models.ForeignKey(BookRequest, blank=True, null=True)
    pub_del_pg = models.BooleanField()  # rename?
    notes = models.CharField(max_length=512, blank=True, null=True)
    pubdel_pages = models.CharField(max_length=512, blank=True, null=True)  # unused?
    original_barcode = models.CharField(max_length=64, blank=True, null=True)
    scope_reason = models.CharField(max_length=16, blank=True, null=True, choices=choices('Damaged','Not Official','Duplicate','No Cases'))
    out_of_scope = models.BooleanField()
    meyer_box_barcode = models.CharField(max_length=32, blank=True, null=True)
    uv_box_barcode = models.CharField(max_length=32, blank=True, null=True)
    meyer_ky_truck = models.CharField(max_length=32, blank=True, null=True)
    meyer_pallet = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Volumes"

    def __str__(self):
        return self.bar_code


class TrackingToolLog(models.Model):
    volume = models.ForeignKey(VolumeMetadata, max_length=64)  # volume?
    type = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=24, blank=True, null=True)
    destination = models.CharField(max_length=128, blank=True, null=True)
    origination = models.CharField(max_length=128, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(TrackingToolUser)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    pstep = models.ForeignKey(ProcessStep, blank=True, null=True)
    exception = models.BooleanField()
    warning = models.BooleanField()
    version_string = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.type

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
