from capi_project.models import Case, Court, Jurisdiction, Reporter

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
    case.save()
    return case
