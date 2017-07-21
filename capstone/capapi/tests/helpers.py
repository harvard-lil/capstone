from capapi.models import Case, CaseUser, Court, Jurisdiction, Reporter
from capapi.utils import generate_unique_slug
import pytz
from datetime import datetime

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

def setup_user(**kwargs):
    password = kwargs.pop('password')
    user = CaseUser(**kwargs)
    user.set_password(password)
    user.save()
    return user

def setup_authenticated_user(**kwargs):
    password = kwargs.pop('password')
    user = CaseUser(**kwargs)
    user.set_password(password)
    user.save()
    user.activation_nonce = "123"
    user.key_expires = datetime.now(pytz.utc)
    user.authenticate_user(activation_nonce=user.activation_nonce)
    user.save()
    return user
