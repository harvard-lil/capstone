from rest_framework.authentication import TokenAuthentication
from capapi.models import APIToken


class CAPAPIUserAuthentication(TokenAuthentication):
    model = APIToken
