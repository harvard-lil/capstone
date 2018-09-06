import os
import binascii
import random
from datetime import timezone
from pathlib import Path

import factory
from pytest_factoryboy import register

from django.template.defaultfilters import slugify

from capapi.models import *
from capdb.models import *


### factories ###

# Calling @pytest_factoryboy.register on each factory exposes it as a pytest fixture.
# For example, CapUserFactory will be available as the fixture "cap_user".

@register
class CapUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = CapUser

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    total_case_allowance = 500
    case_allowance_remaining = 500
    is_staff = False
    is_superuser = False
    is_active = True
    email = factory.LazyAttributeSequence(lambda o, n: '%s_%s%d@example.com' % (o.first_name, o.last_name, n))
    password = factory.PostGenerationMethodCall('set_password', 'pass')
    email_verified = False
    nonce_expires = timezone.now() + timedelta(hours=24)
    activation_nonce = factory.Sequence(lambda n: '%08d' % n)


@register
class TokenFactory(factory.DjangoModelFactory):
    class Meta:
        model = Token

    user = factory.SubFactory(CapUserFactory)
    key = factory.Sequence(lambda n: binascii.hexlify(os.urandom(20)).decode())
    created = timezone.now()


@register
class TrackingToolUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = TrackingToolUser

    privilege_level = '0'
    email = factory.Faker('email')
    created_at = timezone.now()
    updated_at = timezone.now()


@register
class JurisdictionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Jurisdiction
        django_get_or_create = ('name',)

    name = factory.Faker('sentence', nb_words=2)
    name_long = factory.Faker('sentence', nb_words=4)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Making sure our slugs are pretty random so we don't run into IntegrityErrors on save."""
        kwargs['slug'] = '%s-%s' % (slugify(kwargs['name']), random.randrange(1000000000))
        return super()._create(model_class, *args, **kwargs)

@register
class ReporterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Reporter

    full_name = factory.Faker('sentence', nb_words=5)
    short_name = factory.Faker('sentence', nb_words=3)
    start_year = timezone.now().timestamp()
    created_at = timezone.now()
    updated_at = timezone.now()
    volume_count = random.randrange(100000)
    hollis = []

@register
class VolumeFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeMetadata
    barcode = factory.Faker('ean', length=13)
    created_by = factory.SubFactory(TrackingToolUserFactory)
    reporter = factory.SubFactory(ReporterFactory)
    volume_number = factory.Sequence(lambda n: n)

@register
class VolumeXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeXML

    orig_xml = (
            Path(settings.BASE_DIR) /
            "test_data/from_vendor/32044057892259_redacted/32044057892259_redacted_METS.xml"
    ).read_text()
    s3_key = factory.Sequence(lambda n: '%08d' % n)
    metadata = factory.SubFactory(VolumeFactory)


@register
class CourtFactory(factory.DjangoModelFactory):
    class Meta:
        model = Court

    name = factory.Faker('sentence', nb_words=5)
    name_abbreviation = factory.Faker('sentence', nb_words=3)
    jurisdiction = factory.SubFactory(JurisdictionFactory)


@register
class CaseFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseMetadata

    name = factory.Faker('sentence', nb_words=5)
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    first_page = str(random.randrange(1000000))
    last_page = str(int(first_page) + random.randrange(100))
    case_id = factory.Sequence(lambda n: '%08d' % n)
    decision_date = factory.Faker("date_this_century", before_today=True, after_today=False)
    court = factory.SubFactory(CourtFactory)
    volume = factory.SubFactory(VolumeFactory)
    reporter = factory.SubFactory(ReporterFactory)


@register
class CitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Citation

    @factory.lazy_attribute
    def type(self):
        return random.choice(['official', 'parallel'])
    case = factory.SubFactory(CaseFactory)
    cite = factory.Faker('sentence', nb_words=5)


@register
class CaseXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseXML

    orig_xml = (
            Path(settings.BASE_DIR) /
            "test_data/from_vendor/32044057892259_redacted/casemets/32044057892259_redacted_CASEMETS_0001.xml"
    ).read_text()
    volume = factory.SubFactory(VolumeXMLFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """ Add the needed Jurisdiction for this CaseXML's metadata instance to be created on save. """
        parsed = parse_xml(cls.orig_xml)
        JurisdictionFactory(name=jurisdiction_translation[parsed('case|court').attr('jurisdiction').strip()])
        return super()._create(model_class, *args, **kwargs)


@register
class PageXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = PageXML

    orig_xml = (
            Path(settings.BASE_DIR) /
            "test_data/from_vendor/32044057892259_redacted/alto/32044057892259_redacted_ALTO_00008_0.xml"
    ).read_text()
    s3_key = factory.Sequence(lambda n: '%08d' % n)
    volume = factory.SubFactory(VolumeXMLFactory)


@register
class CaseExportFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseExport

    file_name = 'Illinois.zip'
    file = factory.django.FileField(data='fake zip content', filename='Illinois.zip')
    body_format = 'xml'
    public = True
    filter_type = 'jurisdiction'
    filter_id = factory.LazyAttribute(lambda o: JurisdictionFactory.create().pk)