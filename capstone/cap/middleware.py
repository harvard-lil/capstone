from django.contrib.auth.decorators import login_required
from django.urls import reverse


def login_required_middleware(get_response):
    """
        Require user to be logged in for all views. 
    """
    exceptions = {'/admin/login/'}
    def middleware(request):
        if request.path in exceptions:
            return get_response(request)
        return login_required(get_response, login_url=reverse('admin:login'))(request)
    return middleware