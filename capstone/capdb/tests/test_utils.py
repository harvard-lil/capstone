import pytest
from capdb import utils
from capdb.models import Reporter


@pytest.mark.django_db
def test_generate_unique_slug(ingest_metadata):
    unique_name = "Caselaw Access Project"
    slug1 = utils.generate_unique_slug(Reporter(), unique_name, field="full_name")

    assert slug1 == "caselaw-access-project"

    reporter = Reporter.objects.first()
    reporter_name = reporter.full_name
    slug2 = utils.generate_unique_slug(Reporter(), reporter_name, field="full_name")

    assert slug2 == utils.slugify(reporter_name)
