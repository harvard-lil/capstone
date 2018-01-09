import hashlib

from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models, IntegrityError, transaction
from django.utils.text import slugify
from django.utils.encoding import force_bytes, force_str
from model_utils import FieldTracker

from scripts.helpers import special_jurisdiction_cases, jurisdiction_translation, parse_xml, serialize_xml, nsmap
from scripts.process_metadata import get_case_metadata


def choices(*args):
    """ Simple helper to create choices=(('Foo','Foo'),('Bar','Bar'))"""
    return zip(args, args)


class AutoSlugMixin():
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
                    # if we are running in a transaction, we have to run this save in a sub-transaction
                    # to recover from expected IntegrityErrors:
                    if transaction.get_connection().in_atomic_block:
                        with transaction.atomic():
                            return super(AutoSlugMixin, self).save(*args, **kwargs)

                    # otherwise we run with no transaction for speed:
                    else:
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


class CachedLookupMixin():
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

        # if not in cache, attempt to fetch item from DB (raises cls.DoesNotExist if not found):
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
    md5 = models.CharField(max_length=255, blank=True, null=True)

    objects = XMLQuerySet.as_manager()
    tracker = None  # should be set as tracker = FieldTracker() by subclasses

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # update md5
        if self.tracker.has_changed('orig_xml') and not self.tracker.has_changed('md5'):
            self.md5 = self.get_md5()

        return super().save(*args, **kwargs)

    def get_md5(self):
        m = hashlib.md5()
        m.update(force_bytes(self.orig_xml))
        return m.hexdigest()

    def update_related_sums(self, short_identifier, new_checksum, new_size):
        parsed_document = parse_xml(self.orig_xml)
        parsed_document('mets|file[ID="{}"]'.format(short_identifier)).attr["CHECKSUM"] = new_checksum
        parsed_document('mets|file[ID="{}"]'.format(short_identifier)).attr["SIZE"] = new_size
        self.orig_xml = serialize_xml(parsed_document)
        self.save()


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
    name = models.CharField(max_length=100, blank=True)
    name_long = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True, max_length=255)
    whitelisted = models.BooleanField(default=False)

    def __str__(self):
        return self.slug

    class Meta:
        ordering = ['name']

    def get_slug(self):
        return self.name


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
    hollis = ArrayField(models.CharField(max_length=9), blank=True,
                        help_text="This is going to replace the Hollis model")

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
    reporter = models.ForeignKey(Reporter, on_delete=models.DO_NOTHING)
    nominative_volume_number = models.CharField(max_length=1024, blank=True, null=True)
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
    created_by = models.ForeignKey(TrackingToolUser, on_delete=models.DO_NOTHING)
    bibliographic_review = models.CharField(max_length=7, blank=True, null=True,
                                            choices=choices('No', 'Complete', 'Yes'))
    analyst_page_count = models.IntegerField(blank=True, null=True,
                                             help_text="The page number of the last numbered page in the book")
    duplicate = models.BooleanField(default=False)
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

    class Meta:
        verbose_name_plural = "Volumes"

    def __str__(self):
        return self.barcode


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

    def __str__(self):
        return self.metadata_id


class Court(CachedLookupMixin, AutoSlugMixin, models.Model):
    name = models.CharField(max_length=255)
    name_abbreviation = models.CharField(max_length=100, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='courts', on_delete=models.SET_NULL)
    slug = models.SlugField(unique=True, max_length=255, blank=False)

    def __str__(self):
        return self.slug

    class Meta:
        ordering = ['name']

    def get_slug(self):
        return self.name_abbreviation or self.name


class CaseMetadata(AutoSlugMixin, models.Model):
    slug = models.SlugField(max_length=255, unique=True)
    case_id = models.CharField(max_length=64, null=True)
    first_page = models.CharField(max_length=255, null=True, blank=True)
    last_page = models.CharField(max_length=255, null=True, blank=True)
    jurisdiction = models.ForeignKey('Jurisdiction', null=True, related_name='case_metadatas',
                                     on_delete=models.SET_NULL)
    citations = models.ManyToManyField('Citation', related_name='case_metadatas')
    docket_number = models.CharField(max_length=10000, blank=True)
    decision_date = models.DateField(null=True, blank=True)
    decision_date_original = models.CharField(max_length=100, blank=True)
    court = models.ForeignKey('Court', null=True, related_name='case_metadatas', on_delete=models.SET_NULL)
    name = models.TextField(blank=True)
    name_abbreviation = models.CharField(max_length=10000, blank=True)
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


class CaseXML(BaseXMLModel):
    # this field will get dropped once we confirm metadata field is correctly populated:
    case_id = models.CharField(max_length=255, db_index=True)

    metadata = models.OneToOneField(CaseMetadata, blank=True, null=True, related_name='case_xml',
                                    on_delete=models.SET_NULL)
    volume = models.ForeignKey(VolumeXML, related_name='case_xmls',
                               on_delete=models.DO_NOTHING)
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    tracker = FieldTracker()

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        # This compares new XML to the old and updates ALTO files as necessary.
        # We don't yet support adding or removing words from the case body.
        if self.tracker.has_changed('orig_xml') and\
                self.pk is not None and\
                self.tracker.previous('orig_xml') and \
                force_str(self.orig_xml) != self.tracker.previous('orig_xml'):
            # parse objects and get the xml tree objects
            parsed_original_case = parse_xml(self.tracker.previous('orig_xml'))
            parsed_updated_case = parse_xml(self.orig_xml)
            updated_tree = parsed_updated_case.root
            original_tree = parsed_original_case.root

            # If the case is duplicative, just save and move on
            if updated_tree.find('//duplicative:casebody', nsmap) is not None:
                super(CaseXML, self).save(force_insert, force_update, *args, **kwargs)
                return

            original_casebody_tree = parsed_original_case("casebody|casebody")[0]
            updated_casebody_tree = parsed_updated_case("casebody|casebody")[0]

            # get a list of casebody elements and make sure there's no additions or deletions
            original_casebody_xpaths = set([original_tree.getelementpath(element) for element in original_casebody_tree])
            updated_casebody_xpaths = set([updated_tree.getelementpath(element) for element in updated_casebody_tree])

            if len(original_casebody_xpaths - updated_casebody_xpaths) > 0:
                raise Exception("No current support for removing casebody elements")
            if len(updated_casebody_xpaths - original_casebody_xpaths) > 0:
                raise Exception("No current support for adding casebody elements")



            # get the alto files associated with the case in the DB
            alto_files = {}
            for alto in self.pages.all():
                alto_fileid = "_".join((["alto"] + alto.barcode.split('_')[1:3]))
                alto_files[alto_fileid] = alto

            modified_casebody_element = False
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
                    modified_casebody_element = True
                    # go through each alto file that refers to the tag and update the reference
                    for alto in element_pages:
                        alto_page = alto_files[alto]
                        parsed_alto_page = parse_xml(alto_page.orig_xml)
                        structure_tag = parsed_alto_page(
                            'alto|StructureTag[ID="{}"]'.format(original_element.get('id')))
                        if structure_tag is not None:
                            structure_tag.attr["LABEL"] = updated_element.tag
                            alto_page.orig_xml = serialize_xml(parsed_alto_page)
                            alto_page.save(save_case=False)

                # check for modified element text
                if original_element.text != updated_element.text:
                    modified_casebody_element = True
                    # we haven't devised a strategy for dealing with this yet
                    if len(updated_element.text.split(" ")) != len(original_element.text.split(" ")):
                        raise Exception("No current support for adding or removing case text")

                    # Case text elements can include text from multiple alto pages. To compare them you need
                    # to get all of the elements from all of the pages and compare them to a list of words
                    # from the case text.
                    wordcount = 0
                    # loop through each referenced alto file
                    for alto in element_pages:
                        alto_page = alto_files[alto]
                        parsed_alto_page = parse_xml(alto_page.orig_xml)
                        text_block = parsed_alto_page(
                            'alto|TextBlock[TAGREFS="{}"]'.format(original_element.get('id')))
                        words = text_block("alto|String")
                        # loop through each word in the ALTO text block
                        for word in words:
                            updated_word = updated_element.text.split(" ")[wordcount]
                            original_word = original_element.text.split(" ")[wordcount]
                            assert original_word == word.get("CONTENT")
                            if updated_word != original_word:
                                # update ALTO & set the character confidence and word confidence to 100%
                                word.set("WC", "1.00")
                                word.set("CC", "0")
                                word.set("CONTENT", updated_element.text.split(" ")[wordcount])
                            wordcount += 1

                        alto_page.orig_xml = serialize_xml(parsed_alto_page)
                        alto_page.save(save_case=False)


            #update the volume md5
            self.md5 = self.get_md5()
            case_id = parsed_original_case('case|case').attr('caseid')
            short_case_id = "casemets_{}".format(case_id.split('_')[1])
            self.volume.refresh_from_db()
            self.volume.update_related_sums(short_case_id, self.md5, str(len(force_bytes(self.orig_xml))))


            # update the page md5s if a casebody element was modified
            if modified_casebody_element is True:
                for alto in self.pages.all():
                    alto_fileid = "_".join((["alto"] + alto.barcode.split('_')[1:3]))
                    parsed_updated_case('mets|file[ID="{}"]'.format(alto_fileid)).attr["CHECKSUM"] = alto.md5
                    parsed_updated_case('mets|file[ID="{}"]'.format(alto_fileid)).attr["SIZE"] = str(len(force_bytes(self.orig_xml)))

            self.orig_xml=force_str(serialize_xml(parsed_updated_case))

        # save that ish.
        super(CaseXML, self).save(force_insert, force_update, *args, **kwargs)


    def __str__(self):
        return str(self.pk)

    @transaction.atomic
    def create_or_update_metadata(self, update_existing=True):
        """
            creates or updates CaseMetadata object
            - if we want to skip over updating existing case metadata objects
            method returns out.
            - otherwise, create or overwrite properties on related metadata object
        """

        # get or create case.metadata
        case_metadata = self.metadata
        if case_metadata:
            if not update_existing:
                # if case already exists, return out
                return case_metadata
            metadata_created = False
        else:
            case_metadata = CaseMetadata()
            metadata_created = True

        # set up data
        data = get_case_metadata(self.orig_xml)
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

            # set jurisdiction
            if data['volume_barcode'] in special_jurisdiction_cases:
                jurisdiction_name = special_jurisdiction_cases[data["volume_barcode"]]
            else:
                jurisdiction_name = jurisdiction_translation[data["jurisdiction"]]
            case_metadata.jurisdiction = Jurisdiction.get_from_cache(name=jurisdiction_name)

            # set or create court
            # we look up court by name and/or name_abbreviation from data["court"]
            court_kwargs = {k: v for k, v in data["court"].items() if v}
            if court_kwargs:
                try:
                    court = Court.get_from_cache(**court_kwargs)
                except Court.DoesNotExist:
                    court = Court(**court_kwargs)
                    court.save()
                case_metadata.court = court
                if court.jurisdiction_id != case_metadata.jurisdiction_id:
                    court.jurisdiction_id = case_metadata.jurisdiction_id
                    court.save()

        ### Handle citations

        citations = list()

        # first create citations because case slug field relies on citation
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

        # set slug to official citation, or first citation if there is no official
        citation_to_slugify = next((c for c in citations if c.type == 'official'), citations[0])

        case_metadata.save(slug_base=citation_to_slugify.cite)

        # create links between metadata and cites
        # TODO: this may create orphan citations that aren't linked to any case
        case_metadata.citations.set(citations)

        # create link between casexml and metadata
        if metadata_created:
            self.metadata = case_metadata
            self.save(update_fields=['metadata'])

        return case_metadata


class Citation(AutoSlugMixin, models.Model):
    type = models.CharField(max_length=100,
                            choices=(("official", "official"), ("parallel", "parallel")))
    cite = models.CharField(max_length=10000, db_index=True)
    duplicative = models.BooleanField(default=False)
    slug = models.SlugField(max_length=255, unique=True)

    def __str__(self):
        return self.slug

    def get_slug(self):
        return self.cite[:100]


class PageXML(BaseXMLModel):
    barcode = models.CharField(max_length=255, unique=True, db_index=True)
    volume = models.ForeignKey(VolumeXML, related_name='page_xmls',
                               on_delete=models.DO_NOTHING)
    cases = models.ManyToManyField(CaseXML, related_name='pages')
    s3_key = models.CharField(max_length=1024, blank=True, help_text="s3 path")

    tracker = FieldTracker()

    def save(self, force_insert=False, force_update=False, save_case=True, save_volume=True, *args, **kwargs):
        #has our XML changed?
        if self.tracker.has_changed('orig_xml') and\
                self.pk is not None and\
                self.tracker.previous('orig_xml'):
            short_alto_id = "_".join((["alto"] + self.barcode.split('_')[1:3]))
            self.md5 = self.get_md5()

            if save_volume:
                self.volume.update_related_sums(short_alto_id, self.md5, str(len(force_bytes(self.orig_xml))))
            if save_case:
                for case in self.cases.all():
                    case.update_related_sums(short_alto_id, self.md5, str(len(force_bytes(self.orig_xml))))
        super(PageXML, self).save(force_insert, force_update, *args, **kwargs)

    def __str__(self):
        return self.barcode


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
