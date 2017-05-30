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