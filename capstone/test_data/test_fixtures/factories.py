import random
import factory

from django.utils import timezone
from django.template.defaultfilters import slugify

from capapi.models import *
from capdb.models import *


xml_str = "<?xml version='1.0' encoding='utf-8'?><mets xmlns:xlink='http://www.w3.org/1999/xlink'></mets>"

#   helpers for common patterns
def setup_case(**kwargs):
    # set up casemetadata instance
    citation = CitationFactory(type='official')
    case = CaseMetadataFactory(slug=slugify(citation.cite), **kwargs)
    case.citations.add(citation)

    # Add VolumeXML and CaseXML instances
    volume_xml = VolumeXMLFactory(metadata=case.volume)
    casexml = CaseXMLFactory.build(metadata=case, volume=volume_xml)
    casexml.save(create_or_update_metadata=False)

    return case


def setup_casexml(**kwargs):
    return CaseXMLFactory(**kwargs)


def setup_jurisdiction(**kwargs):
    return JurisdictionFactory(**kwargs)


def setup_authenticated_user(**kwargs):
    user = APIUserFactory.create(**kwargs)
    token = APITokenFactory.build(user=user)
    token.save()
    return user


def setup_user(**kwargs):
    return APIUserFactory.create(**kwargs)


def setup_court(**kwargs):
    return CourtFactory(**kwargs)


def setup_reporter(**kwargs):
    return ReporterFactory(**kwargs)


def setup_volume(**kwargs):
    return VolumeMetadataFactory(**kwargs)


def setup_volumexml(**kwargs):
    return VolumeXMLFactory(**kwargs)


def setup_citations(**kwargs):
    return CitationFactory(**kwargs)


#   factories
class APIUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = APIUser

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    total_case_allowance = 500
    case_allowance_remaining = 500
    is_admin = False
    is_active = True
    email = factory.LazyAttributeSequence(lambda o, n: '%s_%s%d@example.com' % (o.first_name, o.last_name, n))
    password = factory.PostGenerationMethodCall('set_password', 'pass')
    key_expires = timezone.now() + timedelta(hours=24)
    activation_nonce = factory.Sequence(lambda n: '%08d' % n)

class APITokenFactory(factory.DjangoModelFactory):
    class Meta:
        model = APIToken

    user = factory.SubFactory(APIUserFactory)
    key = binascii.hexlify(os.urandom(20)).decode()
    created = timezone.now()


class TrackingToolUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = TrackingToolUser

    privilege_level = '0'
    email = factory.Faker('email')
    created_at = timezone.now()
    updated_at = timezone.now()


class JurisdictionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Jurisdiction

    name = factory.Faker('sentence', nb_words=2)
    name_long = factory.Faker('sentence', nb_words=4)
    slug = factory.Sequence(lambda n: '%08d' % n)

class ReporterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Reporter

    full_name = factory.Faker('sentence', nb_words=5)
    short_name = factory.Faker('sentence', nb_words=3)
    start_year = timezone.now().timestamp()
    created_at = timezone.now()
    updated_at = timezone.now()
    hollis = []
    jurisdiction = factory.RelatedFactory(JurisdictionFactory)


class VolumeMetadataFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeMetadata
    barcode = factory.Sequence(lambda n: '%08d' % n)
    created_by = factory.SubFactory(TrackingToolUserFactory)
    reporter = factory.SubFactory(ReporterFactory)


class VolumeXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeXML
    orig_xml = xml_str
    metadata = factory.SubFactory(VolumeMetadataFactory)


class CitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Citation

    @factory.lazy_attribute
    def type(self):
        return random.choice(['official', 'parallel'])

    cite = factory.Faker('sentence', nb_words=5)


class CourtFactory(factory.DjangoModelFactory):
    class Meta:
        model = Court

    name = factory.Faker('sentence', nb_words=5)
    name_abbreviation = factory.Faker('sentence', nb_words=3)
    jurisdiction = factory.SubFactory(JurisdictionFactory)


class CaseMetadataFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseMetadata

    name = factory.Faker('sentence', nb_words=5)
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    first_page = str(random.randrange(1000000))
    last_page = str(int(first_page) + random.randrange(100))
    case_id = factory.Sequence(lambda n: '%08d' % n)
    decision_date = factory.Faker("date_this_century", before_today=True, after_today=False)
    citations = factory.RelatedFactory(CitationFactory)
    court = factory.SubFactory(CourtFactory)
    volume = factory.SubFactory(VolumeMetadataFactory)
    reporter = factory.SubFactory(ReporterFactory)

class CaseXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseXML

    orig_xml = xml_str
    volume = factory.SubFactory(VolumeXMLFactory)


class ReporterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Reporter

    full_name = factory.Faker('sentence', nb_words=5)
    short_name = factory.Faker('sentence', nb_words=3)
    start_year = timezone.now().timestamp()
    created_at = timezone.now()
    updated_at = timezone.now()
    hollis = []
    jurisdiction = factory.RelatedFactory(JurisdictionFactory)
