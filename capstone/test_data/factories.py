import os
import binascii
import random
import pytz
from datetime import datetime, timedelta
import factory

from capapi.models import *
from capdb.models import *

from django.template.defaultfilters import slugify

xml_str = "<?xml version='1.0' encoding='utf-8'?><mets xmlns:xlink='http://www.w3.org/1999/xlink'></mets>"

#   helpers for common patterns
def setup_case(**kwargs):
    # set up casemetadata instance
    volume_xml = VolumeXMLFactory.create()
    casexml = CaseXMLFactory.create(volume=volume_xml)
    citation = CitationFactory.create(type='official')
    case = CaseMetadataFactory.create(
        case_id=casexml.case_id, **kwargs)
    case.citations.add(citation)
    case.jurisdiction.save()
    case.save()

    return case

def setup_jurisdiction(**kwargs):
    jurisdiction = JurisdictionFactory.create()
    jurisdiction.save()

    return jurisdiction

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
    key_expires = datetime.now(pytz.UTC) + timedelta(hours=24)
    activation_nonce = factory.Sequence(lambda n: '%08d' % n)

class APITokenFactory(factory.DjangoModelFactory):
    class Meta:
        model = APIToken

    user = factory.SubFactory(APIUserFactory)
    key = binascii.hexlify(os.urandom(20)).decode()
    created = datetime.now(pytz.UTC)


class VolumeXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = VolumeXML
    orig_xml = xml_str
    barcode = factory.Sequence(lambda n: '%08d' % n)


class JurisdictionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Jurisdiction

    name = factory.Faker('sentence', nb_words=2)
    name_long = factory.Faker('sentence', nb_words=8)
    slug = factory.LazyAttribute(lambda o: '%s' % slugify(o.name))


class CitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Citation

    @factory.lazy_attribute
    def type(self):
        return random.choice(['official', 'parallel'])

    cite = factory.Faker('sentence', nb_words=5)
    slug = factory.LazyAttribute(lambda o: '%s' % slugify(o.cite))


class CourtFactory(factory.DjangoModelFactory):
    class Meta:
        model = Court

    name = factory.Faker('sentence', nb_words=5)
    name_abbreviation = factory.Faker('sentence', nb_words=3)
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    slug = factory.LazyAttribute(lambda o: '%s' % slugify(o.name))


class CaseMetadataFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseMetadata

    name = factory.Faker('sentence', nb_words=5)
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    slug = factory.LazyAttribute(lambda o: '%s' % slugify(o.name))
    first_page = str(random.randrange(1000000))
    last_page = str(int(first_page) + random.randrange(100))
    case_id = factory.Sequence(lambda n: '%08d' % n)
    decision_date = factory.Faker("date_this_century", before_today=True, after_today=False)
    citations = factory.RelatedFactory(CitationFactory)
    court = factory.SubFactory(CourtFactory)


class CaseXMLFactory(factory.DjangoModelFactory):
    class Meta:
        model = CaseXML

    case_id = factory.Sequence(lambda n: '%08d' % n)
    orig_xml = xml_str
    volume = factory.SubFactory(VolumeXMLFactory)


class ReporterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Reporter

    full_name = factory.Faker('sentence', nb_words=5)
    short_name = factory.Faker('sentence', nb_words=3)
    start_year = datetime.now(pytz.UTC).timestamp()
    created_at = datetime.now(pytz.UTC)
    updated_at = datetime.now(pytz.UTC)
    hollis = []
    jurisdiction = factory.RelatedFactory(JurisdictionFactory)
