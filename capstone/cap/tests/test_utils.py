import pytest
from cap import utils
from cap.models import Reporter


@pytest.mark.django_db
def test_generate_unique_slug(ingest_metadata):
    unique_name = "Caselaw Access Project"
    slug1 = utils.generate_unique_slug(Reporter, "full_name", unique_name)

    assert slug1 == "caselaw-access-project"

    reporter = Reporter.objects.first()
    reporter_name = reporter.full_name
    slug2 = utils.generate_unique_slug(Reporter, "full_name", reporter_name)

    assert slug2 == utils.slugify(reporter_name)

    similar_reporter_data = {
        "full_name": reporter.full_name,
        "short_name": reporter.short_name,
        "created_at": reporter.created_at,
        "updated_at": reporter.updated_at,
        "hollis": reporter.hollis,
    }
    reporter.save()

    # TODO: move to testing slug fields

    # similar_reporter = Reporter.objects.create(**similar_reporter_data)
    # slug3 = utils.generate_unique_slug(Reporter, "full_name", reporter_name)
    # assert slug3 == "%s-1" % utils.slugify(reporter_name)
