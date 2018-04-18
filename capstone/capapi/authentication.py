from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token


class CapUserAuthentication(TokenAuthentication):
    model = Token

    def authenticate(self, request):
        api_key = request.query_params.get('api_key', None)
        if api_key:
            return self.authenticate_credentials(api_key)
        else:
            return super(CapUserAuthentication, self).authenticate(request)
