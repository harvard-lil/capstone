from rest_framework.authentication import TokenAuthentication
from capapi.models import APIToken


class CAPAPIUserAuthentication(TokenAuthentication):
    model = APIToken

    def authenticate(self, request):
        api_key = request.query_params.get('api_key', None)
        if api_key:
            return self.authenticate_credentials(api_key)
        else:
            return super(CAPAPIUserAuthentication, self).authenticate(request)
