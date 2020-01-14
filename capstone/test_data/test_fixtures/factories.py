import os
import binascii
import random
from pathlib import Path
import factory
from django.contrib.auth.models import Group
from factory import post_generation
import pytest

from django.template.defaultfilters import slugify

from capapi.models import *
from capdb.models import *


### internal helpers ###

def register(cls):
    """
        Decorator to take a factory class and inject test fixtures. For example,

            @register
            class UserFactory

        will inject the fixtures "user_factory" (equivalent to UserFactory) and "user" (equivalent to UserFactory()).

        This is basically the same as the @register decorator provided by the pytest_factoryboy package,
        but because it's simpler it seems to work better with RelatedFactory and SubFactory.
    """
    camel_case_name = re.sub('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', cls.__name__).lower()

    @pytest.fixture
    def factory_fixture(db):
        return cls

    @pytest.fixture
    def instance_fixture(db):
        return cls()

    globals()[camel_case_name] = factory_fixture
    globals()[camel_case_name.rsplit('_factory', 1)[0]] = instance_fixture

    return cls


### factories ###


@register
class TokenFactory(factory.DjangoModelFactory):
    class Meta:
        model = Token

    key = factory.Sequence(lambda n: binascii.hexlify(os.urandom(20)).decode())
    created = timezone.now()
    # user = factory.SubFactory('test_data.test_fixtures.factories.CapUserFactory')


@register
class CapUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = CapUser

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    total_case_allowance = settings.API_CASE_DAILY_ALLOWANCE
    case_allowance_remaining = settings.API_CASE_DAILY_ALLOWANCE
    is_staff = False
    is_superuser = False
    is_active = True
    email = factory.LazyAttributeSequence(lambda o, n: '%s_%s%d@example.com' % (o.first_name, o.last_name, n))
    password = factory.PostGenerationMethodCall('set_password', 'pass')
    email_verified = False
    nonce_expires = timezone.now() + timedelta(hours=24)
    activation_nonce = factory.Sequence(lambda n: '%08d' % n)
    auth_token = factory.RelatedFactory(TokenFactory, 'user')


@register
class AuthUserFactory(CapUserFactory):
    email_verified = True


@register
class AdminUserFactory(AuthUserFactory):
    is_staff = True
    is_superuser = True


@register
class ContractApproverUserFactory(AuthUserFactory):
    @post_generation
    def add_group(obj, create, extracted, **kwargs):
        obj.groups.add(Group.objects.get_or_create(name='contract_approvers')[0])


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
    slug = factory.Sequence(lambda n: 'slug-%s' % n)


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
class VolumeMetadataFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeMetadata
    barcode = factory.Faker('ean', length=13)
    created_by = factory.SubFactory(TrackingToolUserFactory)
    reporter = factory.SubFactory(ReporterFactory)
    volume_number = factory.Sequence(lambda n: str(n))

_volume_xml = Path(settings.BASE_DIR, "test_data/from_vendor/32044057892259_redacted/32044057892259_redacted_METS.xml").read_text()

@register
class VolumeXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeXML

    orig_xml = factory.Sequence(lambda n: _volume_xml + ' ' * n)  # avoid identical md5 values
    s3_key = factory.Sequence(lambda n: '%08d' % n)
    metadata = factory.SubFactory(VolumeMetadataFactory)


@register
class CourtFactory(factory.DjangoModelFactory):
    class Meta:
        model = Court

    name = factory.Faker('sentence', nb_words=5)
    name_abbreviation = factory.Faker('sentence', nb_words=3)
    jurisdiction = factory.SubFactory(JurisdictionFactory)


@register
class TarFileFactory(factory.DjangoModelFactory):
    class Meta:
        model = TarFile

    volume = factory.SubFactory(VolumeMetadataFactory)
    storage_path = 'unredacted/32044038597167_unredacted'
    hash = '19dae083e7f93e7b7545e50e3ab445076f3f284a061d38e4731e7afeb81cdade'


@register
class CaseStructureFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseStructure

    opinions = []
    ingest_path = 'casemets/32044038597167_unredacted_CASEMETS_0001.xml.gz'
    ingest_source = factory.SubFactory(TarFileFactory)
    metadata = None

@register
class CitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Citation

    type = 'official'
    cite = factory.LazyAttribute(lambda o: "%s U.S. %s" % (random.randint(1,999), random.randint(1, 999)))

    # this should work, per https://factoryboy.readthedocs.io/en/latest/recipes.html#example-django-s-profile ,
    # but actually it throws AttributeError: module has no attribute 'CaseFactory':
    #  case = factory.SubFactory('test_data.test_fixtures.factories.CaseFactory', citations=None)
    # Instead we can do this, as long as we only instantiate this as CitationFactory(case=obj):
    case = None


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
    volume = factory.SubFactory(VolumeMetadataFactory)
    reporter = factory.LazyAttribute(lambda o: o.volume.reporter)
    structure = factory.RelatedFactory(CaseStructureFactory, 'metadata')
    citations = factory.RelatedFactory(CitationFactory, 'case')
    name_abbreviation = "Foo v. Bar"

    @post_generation
    def post(obj, create, extracted, **kwargs):
        obj.frontend_url = obj.get_frontend_url(include_host=False)


_case_xml = Path(settings.BASE_DIR, "test_data/from_vendor/32044057892259_redacted/casemets/32044057892259_redacted_CASEMETS_0001.xml").read_text()

@register
class CaseXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseXML

    orig_xml = factory.Sequence(lambda n: _case_xml.replace('casebody_0001', 'casebody_000%s' % n))  # avoid identical md5/case_id values
    volume = factory.SubFactory(VolumeXMLFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """ Add the needed Jurisdiction for this CaseXML's metadata instance to be created on save. """
        parsed = parse_xml(kwargs['orig_xml'])
        JurisdictionFactory(name=jurisdiction_translation[parsed('case|court').attr('jurisdiction').strip()])
        return super()._create(model_class, *args, **kwargs)


_page_xml = Path(settings.BASE_DIR, "test_data/from_vendor/32044057892259_redacted/alto/32044057892259_redacted_ALTO_00008_0.xml").read_text()

@register
class PageXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = PageXML

    orig_xml = factory.Sequence(lambda n: _page_xml + ' ' * n)  # avoid identical md5 values
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