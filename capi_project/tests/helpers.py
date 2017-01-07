from capi_project.models import Case, Court, Jurisdiction, Reporter
from capi_project.utils import generate_unique_slug
def setup_jurisdiction(**kwargs):
    jur = Jurisdiction(**kwargs)
    jur.save()
    return jur

def setup_reporter(**kwargs):
    rep = Reporter(**kwargs)
    rep.save()
    return rep

def setup_court(**kwargs):
    court = Court(**kwargs)
    court.save()
    return court

def setup_case(**kwargs):
    case = Case(**kwargs)
    slug = generate_unique_slug(Case, case.name_abbreviation)
    case.slug = slug
    case.save()
    return case
