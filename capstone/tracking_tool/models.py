# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from __future__ import unicode_literals

from django.db import models


class Batches(models.Model):
    notes = models.TextField(blank=True, null=True)
    created_by = models.IntegerField()
    sent = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'batches'


class BookRequests(models.Model):
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

    class Meta:
        db_table = 'book_requests'


class Casepages(models.Model):
    bar_code = models.CharField(max_length=64)
    case_id = models.IntegerField()
    seqid = models.CharField(max_length=12)
    caseno = models.CharField(max_length=12)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'casepages'


class Cases(models.Model):
    bar_code = models.CharField(max_length=64)
    redacted_mets_xml = models.CharField(max_length=256, blank=True, null=True)
    unredacted_mets_xml = models.CharField(max_length=256, blank=True, null=True)
    bucket = models.CharField(max_length=32)
    caseno = models.CharField(max_length=12, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    unredacted_xml_invalid = models.CharField(max_length=256, blank=True, null=True)
    redacted_xml_invalid = models.CharField(max_length=256, blank=True, null=True)
    version = models.DateTimeField(blank=True, null=True)
    unredacted_mets_xml_md5 = models.CharField(max_length=32, blank=True, null=True)
    redacted_mets_xml_md5 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        db_table = 'cases'


class Eventloggers(models.Model):
    bar_code = models.CharField(max_length=64)
    type = models.CharField(max_length=128)
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

    class Meta:
        db_table = 'eventloggers'


class Holdingsbooks(models.Model):
    tray = models.CharField(max_length=9)
    barcode = models.CharField(unique=True, max_length=16)
    hollis_no = models.CharField(max_length=12, blank=True, null=True)
    title = models.CharField(max_length=512, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    requested = models.IntegerField(blank=True, null=True)
    inscope = models.IntegerField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'holdingsbooks'


class Holdingstrays(models.Model):
    tray = models.CharField(max_length=9)
    aisle = models.IntegerField()
    ladder = models.IntegerField()
    position = models.IntegerField()
    side = models.CharField(max_length=1)

    class Meta:
        db_table = 'holdingstrays'


class Hollis(models.Model):
    hollis_no = models.CharField(max_length=9, blank=True, null=True)
    reporter_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'hollis'


class InnodataCaseImages(models.Model):
    case_id = models.IntegerField()
    barcode = models.CharField(max_length=15)
    bucket = models.CharField(max_length=48, blank=True, null=True)
    s3key = models.CharField(max_length=255)
    cases3key = models.CharField(max_length=255)
    caseno = models.SmallIntegerField(db_column='caseNo')  # Field name made lowercase.
    docno = models.SmallIntegerField(db_column='docNo')  # Field name made lowercase.
    pageside = models.IntegerField(db_column='pageSide')  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    seqno = models.SmallIntegerField(db_column='seqNo')  # Field name made lowercase.
    version_string = models.CharField(max_length=32, blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'innodata_case_images'


class InnodataPrivateCaseImages(models.Model):
    case_id = models.IntegerField()
    barcode = models.CharField(max_length=15)
    bucket = models.CharField(max_length=48, blank=True, null=True)
    s3key = models.CharField(max_length=255)
    cases3key = models.CharField(max_length=255)
    caseno = models.SmallIntegerField(db_column='caseNo')  # Field name made lowercase.
    docno = models.SmallIntegerField(db_column='docNo')  # Field name made lowercase.
    pageside = models.IntegerField(db_column='pageSide')  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    seqno = models.SmallIntegerField(db_column='seqNo')  # Field name made lowercase.
    version_string = models.CharField(max_length=32, blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'innodata_private_case_images'


class InnodataPrivateCases(models.Model):
    barcode = models.CharField(max_length=15)
    s3key = models.CharField(unique=True, max_length=255)
    etag = models.CharField(db_column='eTag', max_length=32)  # Field name made lowercase.
    caseno = models.SmallIntegerField(db_column='caseNo')  # Field name made lowercase.
    redacted = models.IntegerField()
    deleted = models.IntegerField()
    version_id = models.CharField(max_length=48, blank=True, null=True)
    version_string = models.CharField(max_length=32, blank=True, null=True)
    key_created = models.DateTimeField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    bucket = models.CharField(max_length=32, blank=True, null=True)
    court_count = models.IntegerField()
    caseabbrev_count = models.IntegerField()
    docketnumber_count = models.IntegerField()
    citation_count = models.IntegerField()
    decisiondate_count = models.IntegerField()
    otherdate_count = models.IntegerField()
    publicationstatus_count = models.IntegerField()
    parties_count = models.IntegerField()
    judges_count = models.IntegerField()
    attorneys_count = models.IntegerField()
    opinion_count = models.IntegerField()
    author_count = models.IntegerField()
    p_count = models.IntegerField()
    blockquote_count = models.IntegerField()
    opiniontype_count = models.IntegerField()
    pagelabel_count = models.IntegerField()
    footnote_count = models.IntegerField()
    footnotemark_count = models.IntegerField()
    summary_count = models.IntegerField()
    syllabus_count = models.IntegerField()
    disposition_count = models.IntegerField()
    history_count = models.IntegerField()
    headnotes_count = models.IntegerField()
    bracketnum_count = models.IntegerField()
    key_count = models.IntegerField()
    xml_version = models.IntegerField()
    unknown_tags = models.CharField(max_length=256, blank=True, null=True)
    casename_count = models.IntegerField()
    qastatus = models.IntegerField(blank=True, null=True)
    qanotes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'innodata_private_cases'


class InnodataPrivateImages(models.Model):
    barcode = models.CharField(max_length=15)
    s3key = models.CharField(unique=True, max_length=255)
    etag = models.CharField(db_column='eTag', max_length=32)  # Field name made lowercase.
    docno = models.SmallIntegerField(db_column='docNo')  # Field name made lowercase.
    pageside = models.IntegerField(db_column='pageSide')  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    seqno = models.SmallIntegerField(db_column='seqNo')  # Field name made lowercase.
    redacted = models.IntegerField()
    deleted = models.IntegerField()
    version_id = models.CharField(max_length=48, blank=True, null=True)
    version_string = models.CharField(max_length=32, blank=True, null=True)
    key_created = models.DateTimeField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    bucket = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        db_table = 'innodata_private_images'


class InnodataPrivateVolumes(models.Model):
    barcode = models.CharField(max_length=15)
    s3key = models.CharField(unique=True, max_length=255)
    etag = models.CharField(db_column='eTag', max_length=32)  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    redacted = models.IntegerField()
    deleted = models.IntegerField()
    version_id = models.CharField(max_length=48, blank=True, null=True)
    version_string = models.CharField(max_length=32, blank=True, null=True)
    key_created = models.DateTimeField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    bucket = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        db_table = 'innodata_private_volumes'


class InnodataSharedCaseImages(models.Model):
    case_id = models.IntegerField()
    barcode = models.CharField(max_length=15)
    bucket = models.CharField(max_length=48, blank=True, null=True)
    s3key = models.CharField(max_length=255)
    cases3key = models.CharField(max_length=255)
    caseno = models.SmallIntegerField(db_column='caseNo')  # Field name made lowercase.
    docno = models.SmallIntegerField(db_column='docNo')  # Field name made lowercase.
    pageside = models.IntegerField(db_column='pageSide')  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    seqno = models.SmallIntegerField(db_column='seqNo')  # Field name made lowercase.
    version_string = models.CharField(max_length=32, blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'innodata_shared_case_images'


class InnodataSharedCases(models.Model):
    barcode = models.CharField(max_length=15)
    s3key = models.CharField(unique=True, max_length=255)
    etag = models.CharField(db_column='eTag', max_length=32)  # Field name made lowercase.
    caseno = models.SmallIntegerField(db_column='caseNo')  # Field name made lowercase.
    redacted = models.IntegerField()
    deleted = models.IntegerField()
    version_id = models.CharField(max_length=48, blank=True, null=True)
    version_string = models.CharField(max_length=32, blank=True, null=True)
    key_created = models.DateTimeField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    bucket = models.CharField(max_length=32, blank=True, null=True)
    court_count = models.IntegerField()
    casename_count = models.IntegerField()
    caseabbrev_count = models.IntegerField()
    docketnumber_count = models.IntegerField()
    citation_count = models.IntegerField()
    decisiondate_count = models.IntegerField()
    otherdate_count = models.IntegerField()
    publicationstatus_count = models.IntegerField()
    parties_count = models.IntegerField()
    judges_count = models.IntegerField()
    attorneys_count = models.IntegerField()
    opinion_count = models.IntegerField()
    author_count = models.IntegerField()
    p_count = models.IntegerField()
    blockquote_count = models.IntegerField()
    opiniontype_count = models.IntegerField()
    pagelabel_count = models.IntegerField()
    footnote_count = models.IntegerField()
    footnotemark_count = models.IntegerField()
    summary_count = models.IntegerField()
    syllabus_count = models.IntegerField()
    disposition_count = models.IntegerField()
    history_count = models.IntegerField()
    headnotes_count = models.IntegerField()
    bracketnum_count = models.IntegerField()
    key_count = models.IntegerField()
    xml_version = models.IntegerField()
    unknown_tags = models.CharField(max_length=256, blank=True, null=True)
    qastatus = models.IntegerField(blank=True, null=True)
    qanotes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'innodata_shared_cases'


class InnodataSharedImages(models.Model):
    barcode = models.CharField(max_length=15)
    s3key = models.CharField(unique=True, max_length=255)
    etag = models.CharField(db_column='eTag', max_length=32)  # Field name made lowercase.
    docno = models.SmallIntegerField(db_column='docNo')  # Field name made lowercase.
    pageside = models.IntegerField(db_column='pageSide')  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    seqno = models.SmallIntegerField(db_column='seqNo')  # Field name made lowercase.
    redacted = models.IntegerField()
    deleted = models.IntegerField()
    version_id = models.CharField(max_length=48, blank=True, null=True)
    version_string = models.CharField(max_length=32, blank=True, null=True)
    key_created = models.DateTimeField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    bucket = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        db_table = 'innodata_shared_images'


class InnodataSharedVolumes(models.Model):
    barcode = models.CharField(max_length=15)
    s3key = models.CharField(unique=True, max_length=255)
    etag = models.CharField(db_column='eTag', max_length=32)  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    redacted = models.IntegerField()
    deleted = models.IntegerField()
    version_id = models.CharField(max_length=48, blank=True, null=True)
    version_string = models.CharField(max_length=32, blank=True, null=True)
    key_created = models.DateTimeField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    bucket = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        db_table = 'innodata_shared_volumes'


class Migrations(models.Model):
    migration = models.CharField(max_length=255)
    batch = models.IntegerField()

    class Meta:
        db_table = 'migrations'


class Pages(models.Model):
    bar_code = models.CharField(max_length=64)
    redacted_tiff = models.CharField(max_length=256, blank=True, null=True)
    unredacted_tiff = models.CharField(max_length=256, blank=True, null=True)
    redacted_jp2 = models.CharField(max_length=256, blank=True, null=True)
    unredacted_jp2 = models.CharField(max_length=256, blank=True, null=True)
    redacted_alto_xml = models.CharField(max_length=256, blank=True, null=True)
    unredacted_alto_xml = models.CharField(max_length=256, blank=True, null=True)
    bucket = models.CharField(max_length=32)
    seqid = models.CharField(max_length=12)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    version = models.DateTimeField(blank=True, null=True)
    unredacted_alto_xml_md5 = models.CharField(max_length=32, blank=True, null=True)
    redacted_alto_xml_md5 = models.CharField(max_length=32, blank=True, null=True)
    unredacted_jp2_md5 = models.CharField(max_length=32, blank=True, null=True)
    redacted_jp2_md5 = models.CharField(max_length=32, blank=True, null=True)
    unredacted_tiff_md5 = models.CharField(max_length=32, blank=True, null=True)
    redacted_tiff_md5 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        db_table = 'pages'


class Preferences(models.Model):
    id = models.CharField(primary_key=True, max_length=30)
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=30)
    privlevel = models.CharField(max_length=30)
    value = models.TextField(blank=True, null=True)
    default_value = models.CharField(max_length=512, blank=True, null=True)
    updated_by = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'preferences'


class PrivateReporterTagStats(models.Model):
    created_at = models.DateTimeField()
    reporter_id = models.IntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    case_count = models.IntegerField(blank=True, null=True)
    case_missing_count = models.IntegerField(blank=True, null=True)
    court_count = models.IntegerField(blank=True, null=True)
    casename_count = models.IntegerField(blank=True, null=True)
    caseabbrev_count = models.IntegerField(blank=True, null=True)
    docketnumber_count = models.IntegerField(blank=True, null=True)
    citation_count = models.IntegerField(blank=True, null=True)
    decisiondate_count = models.IntegerField(blank=True, null=True)
    otherdate_count = models.IntegerField(blank=True, null=True)
    publicationstatus_count = models.IntegerField(blank=True, null=True)
    parties_count = models.IntegerField(blank=True, null=True)
    judges_count = models.IntegerField(blank=True, null=True)
    attorneys_count = models.IntegerField(blank=True, null=True)
    opinion_count = models.IntegerField(blank=True, null=True)
    author_count = models.IntegerField(blank=True, null=True)
    p_count = models.IntegerField(blank=True, null=True)
    blockquote_count = models.IntegerField(blank=True, null=True)
    opiniontype_count = models.IntegerField(blank=True, null=True)
    pagelabel_count = models.IntegerField(blank=True, null=True)
    footnote_count = models.IntegerField(blank=True, null=True)
    footnotemark_count = models.IntegerField(blank=True, null=True)
    summary_count = models.IntegerField(blank=True, null=True)
    syllabus_count = models.IntegerField(blank=True, null=True)
    disposition_count = models.IntegerField(blank=True, null=True)
    history_count = models.IntegerField(blank=True, null=True)
    headnotes_count = models.IntegerField(blank=True, null=True)
    bracketnum_count = models.IntegerField(blank=True, null=True)
    key_count = models.IntegerField(blank=True, null=True)
    unknown_tags = models.IntegerField(blank=True, null=True)
    qastatus = models.IntegerField(blank=True, null=True)
    qanotes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'private_reporter_tag_stats'


class PrivateVolumeTagStats(models.Model):
    created_at = models.DateTimeField()
    reporter_id = models.IntegerField(blank=True, null=True)
    bar_code = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    case_count = models.IntegerField(blank=True, null=True)
    case_missing_count = models.IntegerField(blank=True, null=True)
    court_count = models.IntegerField(blank=True, null=True)
    casename_count = models.IntegerField(blank=True, null=True)
    caseabbrev_count = models.IntegerField(blank=True, null=True)
    docketnumber_count = models.IntegerField(blank=True, null=True)
    citation_count = models.IntegerField(blank=True, null=True)
    decisiondate_count = models.IntegerField(blank=True, null=True)
    otherdate_count = models.IntegerField(blank=True, null=True)
    publicationstatus_count = models.IntegerField(blank=True, null=True)
    parties_count = models.IntegerField(blank=True, null=True)
    judges_count = models.IntegerField(blank=True, null=True)
    attorneys_count = models.IntegerField(blank=True, null=True)
    opinion_count = models.IntegerField(blank=True, null=True)
    author_count = models.IntegerField(blank=True, null=True)
    p_count = models.IntegerField(blank=True, null=True)
    blockquote_count = models.IntegerField(blank=True, null=True)
    opiniontype_count = models.IntegerField(blank=True, null=True)
    pagelabel_count = models.IntegerField(blank=True, null=True)
    footnote_count = models.IntegerField(blank=True, null=True)
    footnotemark_count = models.IntegerField(blank=True, null=True)
    summary_count = models.IntegerField(blank=True, null=True)
    syllabus_count = models.IntegerField(blank=True, null=True)
    disposition_count = models.IntegerField(blank=True, null=True)
    history_count = models.IntegerField(blank=True, null=True)
    headnotes_count = models.IntegerField(blank=True, null=True)
    bracketnum_count = models.IntegerField(blank=True, null=True)
    key_count = models.IntegerField(blank=True, null=True)
    unknown_tags = models.IntegerField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    publicationyear = models.IntegerField(blank=True, null=True)
    qastatus = models.IntegerField(blank=True, null=True)
    qanotes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'private_volume_tag_stats'


class ProjectVolume(models.Model):
    bar_code = models.CharField(max_length=64)
    project_id = models.CharField(max_length=24)

    class Meta:
        db_table = 'project_volume'


class Projects(models.Model):
    name = models.CharField(max_length=24)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'projects'


class Pstep(models.Model):
    step_id = models.CharField(unique=True, max_length=255, primary_key=True)
    type = models.CharField(max_length=1, blank=True, null=True)
    name = models.CharField(max_length=24, blank=True, null=True)
    prereq = models.CharField(max_length=1024, blank=True, null=True)
    desc = models.CharField(max_length=256)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'pstep'


class Reporters(models.Model):
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

    class Meta:
        db_table = 'reporters'


class S3KeyErrors(models.Model):
    bucket = models.CharField(max_length=48, blank=True, null=True)
    error_type = models.CharField(max_length=12, blank=True, null=True)
    error_text = models.TextField(blank=True, null=True)
    key_created = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 's3_key_errors'


class S3ScannerOutput(models.Model):
    barcode = models.CharField(max_length=15)
    s3key = models.CharField(unique=True, max_length=90)
    etag = models.CharField(db_column='eTag', max_length=32)  # Field name made lowercase.
    fileformat = models.CharField(db_column='fileFormat', max_length=3)  # Field name made lowercase.
    version_id = models.CharField(max_length=48, blank=True, null=True)
    docno = models.SmallIntegerField(db_column='docNo', blank=True, null=True)  # Field name made lowercase.
    pageside = models.IntegerField(db_column='pageSide', blank=True, null=True)  # Field name made lowercase.
    seqno = models.SmallIntegerField(db_column='seqNo', blank=True, null=True)  # Field name made lowercase.
    version_string = models.CharField(max_length=32, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    bucket = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        db_table = 's3_scanner_output'


class ServerStats(models.Model):
    fqdn = models.CharField(max_length=256)
    ip = models.CharField(max_length=16)
    type = models.CharField(max_length=8)
    qcwait = models.IntegerField(blank=True, null=True)
    xferwait = models.IntegerField(blank=True, null=True)
    pswait = models.IntegerField(blank=True, null=True)
    df = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'server_stats'


class SharedReporterTagStats(models.Model):
    created_at = models.DateTimeField()
    reporter_id = models.IntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    case_count = models.IntegerField(blank=True, null=True)
    case_missing_count = models.IntegerField(blank=True, null=True)
    court_count = models.IntegerField(blank=True, null=True)
    casename_count = models.IntegerField(blank=True, null=True)
    caseabbrev_count = models.IntegerField(blank=True, null=True)
    docketnumber_count = models.IntegerField(blank=True, null=True)
    citation_count = models.IntegerField(blank=True, null=True)
    decisiondate_count = models.IntegerField(blank=True, null=True)
    otherdate_count = models.IntegerField(blank=True, null=True)
    publicationstatus_count = models.IntegerField(blank=True, null=True)
    parties_count = models.IntegerField(blank=True, null=True)
    judges_count = models.IntegerField(blank=True, null=True)
    attorneys_count = models.IntegerField(blank=True, null=True)
    opinion_count = models.IntegerField(blank=True, null=True)
    author_count = models.IntegerField(blank=True, null=True)
    p_count = models.IntegerField(blank=True, null=True)
    blockquote_count = models.IntegerField(blank=True, null=True)
    opiniontype_count = models.IntegerField(blank=True, null=True)
    pagelabel_count = models.IntegerField(blank=True, null=True)
    footnote_count = models.IntegerField(blank=True, null=True)
    footnotemark_count = models.IntegerField(blank=True, null=True)
    summary_count = models.IntegerField(blank=True, null=True)
    syllabus_count = models.IntegerField(blank=True, null=True)
    disposition_count = models.IntegerField(blank=True, null=True)
    history_count = models.IntegerField(blank=True, null=True)
    headnotes_count = models.IntegerField(blank=True, null=True)
    bracketnum_count = models.IntegerField(blank=True, null=True)
    key_count = models.IntegerField(blank=True, null=True)
    unknown_tags = models.IntegerField(blank=True, null=True)
    qastatus = models.IntegerField(blank=True, null=True)
    qanotes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'shared_reporter_tag_stats'


class SharedVolumeTagStats(models.Model):
    created_at = models.DateTimeField()
    reporter_id = models.IntegerField(blank=True, null=True)
    bar_code = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    case_count = models.IntegerField(blank=True, null=True)
    case_missing_count = models.IntegerField(blank=True, null=True)
    court_count = models.IntegerField(blank=True, null=True)
    casename_count = models.IntegerField(blank=True, null=True)
    caseabbrev_count = models.IntegerField(blank=True, null=True)
    docketnumber_count = models.IntegerField(blank=True, null=True)
    citation_count = models.IntegerField(blank=True, null=True)
    decisiondate_count = models.IntegerField(blank=True, null=True)
    otherdate_count = models.IntegerField(blank=True, null=True)
    publicationstatus_count = models.IntegerField(blank=True, null=True)
    parties_count = models.IntegerField(blank=True, null=True)
    judges_count = models.IntegerField(blank=True, null=True)
    attorneys_count = models.IntegerField(blank=True, null=True)
    opinion_count = models.IntegerField(blank=True, null=True)
    author_count = models.IntegerField(blank=True, null=True)
    p_count = models.IntegerField(blank=True, null=True)
    blockquote_count = models.IntegerField(blank=True, null=True)
    opiniontype_count = models.IntegerField(blank=True, null=True)
    pagelabel_count = models.IntegerField(blank=True, null=True)
    footnote_count = models.IntegerField(blank=True, null=True)
    footnotemark_count = models.IntegerField(blank=True, null=True)
    summary_count = models.IntegerField(blank=True, null=True)
    syllabus_count = models.IntegerField(blank=True, null=True)
    disposition_count = models.IntegerField(blank=True, null=True)
    history_count = models.IntegerField(blank=True, null=True)
    headnotes_count = models.IntegerField(blank=True, null=True)
    bracketnum_count = models.IntegerField(blank=True, null=True)
    key_count = models.IntegerField(blank=True, null=True)
    unknown_tags = models.IntegerField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    publicationyear = models.IntegerField(blank=True, null=True)
    qastatus = models.IntegerField(blank=True, null=True)
    qanotes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'shared_volume_tag_stats'


class Statcache(models.Model):
    name = models.CharField(max_length=32, blank=True, null=True)
    updated_at = models.DateTimeField()
    created_at = models.DateTimeField(blank=True, null=True)
    value = models.IntegerField(blank=True, null=True)
    offset = models.SmallIntegerField(blank=True, null=True)
    json = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'statcache'


class Users(models.Model):
    privlevel = models.CharField(max_length=3)
    email = models.CharField(max_length=320)
    password = models.CharField(max_length=64)
    active = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    remember_token = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'users'


class VolumeBackups(models.Model):
    bar_code = models.CharField(max_length=64)
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

    class Meta:
        db_table = 'volume_backups'


class Volumes(models.Model):
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

    class Meta:
        db_table = 'volumes'