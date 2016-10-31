from django.conf.urls import url
from django.contrib import admin
from django.conf.urls import url, include
from django.contrib.auth.models import User
from rest_framework import routers

from capi_project import views
from capi_project.models import Case

router = routers.DefaultRouter()
router.register(r'cases', views.CaseViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^login/$', views.LoginView.as_view()),
    url(r'^admin', include(admin.site.urls)),
    url(r'^register/?$', views.SignupView.as_view()),
    url(r'^verify-user/(?P<user_id>[\d+]+)/(?P<activation_nonce>[0-9a-z]+)/?$', views.verify_user),
    url(r'^cases/(?P<jurisdiction__iexact>[\w ]+)/?$', views.CaseViewSet.as_view({'get':'list'})),
    url(r'^cases/(?P<jurisdiction__iexact>[\w ]+)/(?P<court__icontains>[\w ]+)/?$', views.CaseViewSet.as_view({'get':'list'})),
    url(r'^cases/(?P<jurisdiction__iexact>[\w ]+)/(?P<court__icontains>[\w ]+)/(?P<name__icontains>[\w ]+)?$', views.CaseViewSet.as_view({'get':'list'})),
]
