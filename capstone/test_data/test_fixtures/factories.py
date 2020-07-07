import os
import binascii
import random
from datetime import date
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
class EmailBlocklistFactory(factory.DjangoModelFactory):
    class Meta:
        model = EmailBlocklist


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
    start_year = 1900
    end_year = 2000
    created_at = timezone.now()
    updated_at = timezone.now()
    volume_count = 10
    hollis = []

    @post_generation
    def jurisdictions(obj, create, extracted, **kwargs):
        if not create:
            return
        obj.jurisdictions.set(extracted or [JurisdictionFactory()])


@register
class VolumeMetadataFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeMetadata
    barcode = factory.Faker('ean', length=13)
    created_by = factory.SubFactory(TrackingToolUserFactory)
    reporter = factory.SubFactory(ReporterFactory)
    volume_number = factory.Sequence(lambda n: str(n))
    pdf_file = 'fake_volume.pdf'  # stored in test_data/downloads/

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
class CitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Citation

    type = 'official'
    cite = factory.LazyAttribute(lambda o: "%s U.S. %s" % (random.randint(1,999), random.randint(1, 999)))
    # This doesn't work because the case factory needs the cite to already exist to generate frontend_url:
    # case = factory.SubFactory('test_data.test_fixtures.factories.CaseFactory', citations=None)
    case = None


@register
class CaseBodyCacheFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseBodyCache

    text = factory.Sequence(lambda n: 'Case text %s' % n)
    html = factory.Sequence(lambda n: '<p>Case html %s</p>' % n)
    xml = factory.Sequence(lambda n: "<?xml version='1.0' encoding='utf-8'?><p>Case xml %s</p>" % n)
    json = {
        "attorneys": [
            "Matthew J. Dudley, for appellant.",
            "Camerina I. Brokaw-Zorrozua (of Maxey Law Office PS), for respondent."
        ],
        "head_matter": "head matter",
        "parties": [
            "In the Matter of the Marriage of Christy Lyle, Respondent, and Keith Lyle, Appellant."
        ],
        "opinions": [
            {
                "author": "Pennell, J.",
                "text": "Opinion text",
                "type": "majority"
            }
        ],
        "judges": [
            "Fearing, C.J., and Korsmo, J., concur."
        ],
        "corrections": ""
    }


@register
class TarFileFactory(factory.DjangoModelFactory):
    class Meta:
        model = TarFile
    volume = factory.SubFactory(VolumeMetadataFactory)
    storage_path = factory.LazyAttribute(lambda o: "redacted/%s_redacted" % o.volume.pk)
    hash = "347cf171537b17f9943a752ec042a29b3fc85290e3bb0ff00c6e6819f4371dec"


@register
class PageStructureFactory(factory.DjangoModelFactory):
    class Meta:
        model = PageStructure

    volume = factory.SubFactory(VolumeMetadataFactory)
    order = factory.Sequence(lambda n: n)
    label = factory.Sequence(lambda n: str(n))

    blocks = [
        {
            "id": id,
            "rect": [226.0, 1320.0, 752.0, 926.0],
            "class": "p",
            "tokens": [
                ["line", {"rect": [267, 1320, 711, 38]}],
                ["font", {"id": 1}],
                ["ocr", {"wc": 1.0, "rect": [267, 1320, 62, 30]}], "Case text %s" % i, ["/ocr"],
                ["/font"],
                ["/line"]
            ]
        } for i, id in enumerate(["BL_81.3", "BL_83.6", "BL_83.7", "BL_83.16"])
    ]
    font_names = {"1": "Style_1"}

    image_file_name = factory.LazyAttribute(lambda o: "%s_%s_1.tif" % (o.volume.pk, o.order))
    width = 1934
    height = 2924
    deskew = "RED.transform=(0.9999980000006666, -0.0019999986666669333, 0.0019999986666669333, 0.9999980000006666, -0.08000000000004093, -3.927999999999889)"

    ingest_source = factory.SubFactory(TarFileFactory)
    ingest_path = factory.LazyAttribute(lambda o: " alto/%s_unredacted_ALTO_%s_1.xml.gz" % (o.volume.pk, o.order))

    @post_generation
    def post(obj, create, extracted, **kwargs):
        if not create:
            return
        CaseFont.objects.get_or_create(id=1, defaults={'family': 'Arial', 'size': '38.00', 'style': '', 'type': 'serif', 'width': 'proportional'})


@register
class CaseStructureFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseStructure

    metadata = None
    ingest_source = factory.SubFactory(TarFileFactory)
    ingest_path = factory.LazyAttribute(lambda o: "casemets/%s_unredacted_CASEMETS_0001.xml.gz" % o.ingest_source.volume.pk)
    opinions = [
        {
            "type": "head",
            "paragraphs": [{"id": "b81-4", "class": "parties", "block_ids": ["BL_81.3"]}],
        },
        {
            "type": "majority",
            "paragraphs": [{"id": "b83-6", "class": "p", "block_ids": ["BL_83.6", "BL_83.7"]}],
            "footnotes": [
                {
                    "id": "footnote_1_1",
                    "label": "1",
                    "paragraphs": [{"id": "b83-11", "class": "p", "block_ids": ["BL_83.16"]}],
                }
            ],
        }
    ]

    @post_generation
    def pages(obj, create, extracted, **kwargs):
        if not create:
            return
        obj.pages.set(extracted or [PageStructureFactory(volume=obj.metadata.volume, ingest_source=obj.ingest_source)])


@register
class CaseFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseMetadata

    name = factory.Sequence(lambda n: 'First Foo%s versus First Bar%s' % (n, n))
    name_abbreviation = factory.Sequence(lambda n: 'Foo%s v. Bar%s' % (n, n))
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    first_page = factory.Sequence(lambda n: str((n+1)*4))
    last_page = factory.LazyAttribute(lambda o: str(int(o.first_page)+4))
    first_page_order = factory.LazyAttribute(lambda o: int(o.first_page)+2)
    last_page_order = factory.LazyAttribute(lambda o: int(o.last_page)+2)
    case_id = factory.Sequence(lambda n: '%08d' % n)
    decision_date = factory.Sequence(lambda n: date(1900+(n%100), 1, 1))
    decision_date_original = factory.LazyAttribute(lambda o: o.decision_date.strftime("%Y-%m-%d"))
    court = factory.SubFactory(CourtFactory)
    volume = factory.SubFactory(VolumeMetadataFactory)
    reporter = factory.LazyAttribute(lambda o: o.volume.reporter)
    structure = factory.RelatedFactory(CaseStructureFactory, 'metadata')
    citations = factory.RelatedFactory(CitationFactory, 'case')
    body_cache = factory.RelatedFactory(CaseBodyCacheFactory, 'metadata')

    @post_generation
    def post(obj, create, extracted, **kwargs):
        obj.frontend_url = obj.get_frontend_url(include_host=False)
        if not create:
            return
        if settings.MAINTAIN_ELASTICSEARCH_INDEX:
            obj.reindex()


@register
class UnrestrictedCaseFactory(CaseFactory):
    jurisdiction = factory.SubFactory(JurisdictionFactory, whitelisted=True)


@register
class RestrictedCaseFactory(CaseFactory):
    jurisdiction = factory.SubFactory(JurisdictionFactory, whitelisted=False)


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


@register
class ExtractedCitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = ExtractedCitation

    cite = factory.LazyAttribute(lambda o: "%s U.S. %s" % (random.randint(1,999), random.randint(1, 999)))
    cited_by = factory.SubFactory(CaseFactory)


