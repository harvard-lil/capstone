from django.contrib.postgres.fields import JSONField
from django.db import models


### custom column types ###

class XMLField(models.TextField):
    """
        Column type for Postgres XML columns.
    """
    def db_type(self, connection):
        return 'xml'


### models ###

class Volume(models.Model):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    orig_xml = XMLField()

    def __str__(self):
        return self.barcode

class Case(models.Model):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    orig_xml = XMLField()
    volume = models.ForeignKey(Volume)

    def __str__(self):
        return self.barcode

class Page(models.Model):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    orig_xml = XMLField()
    volume = models.ForeignKey(Volume)
    cases = models.ManyToManyField(Case, related_name='pages')

    def __str__(self):
        return self.barcode

# class Changeset(models.Model):
#     transaction_timestamp = models.DateTimeField(auto_now_add=True)
#     message = models.CharField(max_length=255)

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


#
# Here's the Tracking Tool port models
#

class VolumeMetadata(models.Model):
    bar_code = models.CharField(unique=True, max_length=64, primary_key=True)
    hollis_no = models.CharField(max_length=128)
    volume = models.CharField(max_length=64, blank=True, null=True)
    publicationdate = models.DateField(blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publicationyear = models.IntegerField(blank=True, null=True)
    reporter_id = models.IntegerField(blank=True, null=True)
    publicationdategranularity = models.CharField(max_length=1, blank=True, null=True)
    nom_volume = models.CharField(max_length=1024, blank=True, null=True)
    nominative_name = models.CharField(max_length=1024, blank=True, null=True)
    series_volume = models.CharField(max_length=1024, blank=True, null=True)
    spine_start_date = models.IntegerField(blank=True, null=True)
    spine_end_date = models.IntegerField(blank=True, null=True)
    start_date = models.IntegerField(blank=True, null=True)
    end_date = models.IntegerField(blank=True, null=True)
    page_start_date = models.IntegerField(blank=True, null=True)
    page_end_date = models.IntegerField(blank=True, null=True)
    redaction_profile = models.CharField(max_length=1, blank=True, null=True)
    contributing_library = models.CharField(max_length=256, blank=True, null=True)
    rare = models.CharField(max_length=255, blank=True, null=True)
    hscrev = models.CharField(max_length=255, blank=True, null=True)
    hsc_accession = models.DateTimeField(blank=True, null=True)
    needs_repair = models.CharField(max_length=255, blank=True, null=True)
    missing_text_pages = models.CharField(max_length=10000, blank=True, null=True)
    created_by = models.IntegerField()
    bibrev = models.CharField(max_length=1, blank=True, null=True)
    pages = models.IntegerField(blank=True, null=True)
    dup = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    replaced_pages = models.CharField(max_length=1024, blank=True, null=True)
    cases = models.IntegerField(blank=True, null=True)
    marginalia = models.IntegerField(blank=True, null=True)
    pop = models.CharField(max_length=1024, blank=True, null=True)
    title = models.CharField(max_length=1024, blank=True, null=True)
    handfeed = models.IntegerField(blank=True, null=True)
    imgct = models.IntegerField(blank=True, null=True)
    hold = models.IntegerField(blank=True, null=True)
    request_id = models.IntegerField(blank=True, null=True)
    pub_del_pg = models.IntegerField(blank=True, null=True)
    notes = models.CharField(max_length=512, blank=True, null=True)
    pubdel_pages = models.CharField(max_length=512, blank=True, null=True)
    original_barcode = models.CharField(max_length=64, blank=True, null=True)
    scope_reason = models.CharField(max_length=16, blank=True, null=True)
    out_of_scope = models.IntegerField()
    meyer_box_barcode = models.CharField(max_length=32, blank=True, null=True)
    uv_box_barcode = models.CharField(max_length=32, blank=True, null=True)
    meyer_ky_truck = models.CharField(max_length=32, blank=True, null=True)
    meyer_pallet = models.CharField(max_length=32, blank=True, null=True)

class TrackingToolUsers(models.Model):
    privlevel = models.CharField(max_length=3)
    email = models.CharField(max_length=320)
    password = models.CharField(max_length=64)
    active = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    remember_token = models.CharField(max_length=100, blank=True, null=True)

class Reporter(models.Model):
    state = models.CharField(max_length=64, blank=True, null=True)
    reporter = models.CharField(max_length=256)
    short = models.CharField(max_length=64)
    start_date = models.IntegerField(blank=True, null=True)
    end_date = models.IntegerField(blank=True, null=True)
    volumes = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    original_volumes = models.IntegerField(blank=True, null=True)
    original_start_date = models.CharField(max_length=4, blank=True, null=True)
    original_end_date = models.CharField(max_length=4, blank=True, null=True)
    observed_start_date = models.IntegerField(blank=True, null=True)
    observed_end_date = models.IntegerField(blank=True, null=True)
    observed_volumes = models.IntegerField(blank=True, null=True)

class ProcessStep(models.Model):
    step_id = models.CharField(unique=True, max_length=255)
    type = models.CharField(max_length=1, blank=True, null=True)
    name = models.CharField(max_length=24, blank=True, null=True)
    prereq = models.CharField(max_length=1024, blank=True, null=True)
    desc = models.CharField(max_length=256)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

class Hollis(models.Model):
    hollis_no = models.CharField(max_length=9, blank=True, null=True)
    reporter_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)

class TrackingToolLog(models.Model):
    bar_code = models.CharField(max_length=64)
    type = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=24, blank=True, null=True)
    destination = models.CharField(max_length=128, blank=True, null=True)
    origination = models.CharField(max_length=128, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    pstep_id = models.CharField(max_length=48, blank=True, null=True)
    exception = models.IntegerField(blank=True, null=True)
    warning = models.IntegerField(blank=True, null=True)
    version_string = models.CharField(max_length=32, blank=True, null=True)

class Batch(models.Model):
    notes = models.TextField(blank=True, null=True)
    created_by = models.IntegerField()
    sent = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

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