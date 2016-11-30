from django.conf.urls import url
from django.contrib import admin
from django.conf.urls import url, include
from django.shortcuts import render
from rest_framework import routers

from capi_project import views

router = routers.DefaultRouter()
router.register(r'cases', views.CaseViewSet)
router.register(r'account', views.UserViewSet)
from rest_framework_swagger.views import get_swagger_view

schema_view = get_swagger_view(title='CAP API')

urlpatterns = [

    url(r'^$', schema_view),
    url(r'^', include(router.urls)),

    url(r'^admin', include(admin.site.urls)),
    url(r'^verify-user/(?P<user_id>[\d+]+)/(?P<activation_nonce>[0-9a-z]+)/?$', views.verify_user),

    url(r'^cases/jurisdictions/?$', views.list_jurisdictions, name='list-jurisdictions'),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/?$', views.CaseViewSet.as_view({'get':'list'}), name='list-for-jurisdiction'),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/reporters/?$', views.list_reporters, name='list-reporters'),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\w+]+)', views.CaseViewSet.as_view({'get':'list'})),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\w+]+)/volumes/?$', views.list_volumes),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\w+]+)/(?P<volume>[\d+]+)/?$', views.CaseViewSet.as_view({'get':'list'})),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\w+]+)/(?P<volume>[\d+]+)/(?P<first_page>[\d+]+)/?$', views.CaseViewSet.as_view({'get':'list'})),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\w+]+)/(?P<volume>[\d+]+)/(?P<first_page>[\d+]+)/(?P<shortname>[\d+]+)?$', views.get_case),
]
