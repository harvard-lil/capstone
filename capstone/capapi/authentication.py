import rest_framework.authentication

from .resources import wrap_user


class WrapUserMixin:
    def authenticate(self, request):
        """
            Ensure that users fetched via DRF auth will have wrap_user() called on them.
            This is also done in capapi.middleware.AuthenticationMiddleware for regular Django auth.
        """
        user_and_token = super().authenticate(request)
        if not user_and_token:
            return None
        user, token = user_and_token
        user = wrap_user(request, user)
        return user, token


# apply WrapUserMixin to each authentication backend
class TokenAuthentication(WrapUserMixin, rest_framework.authentication.TokenAuthentication):
    pass
class SessionAuthentication(WrapUserMixin, rest_framework.authentication.SessionAuthentication):
    pass