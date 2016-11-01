from django.conf.urls import url
from django.contrib import admin
from django.conf.urls import url, include
from django.shortcuts import render
from rest_framework import routers

from capi_project import views

router = routers.DefaultRouter()
router.register(r'cases', views.CaseViewSet)
router.register(r'account', views.UserViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^login/$', views.LoginView.as_view()),
    url(r'^admin', include(admin.site.urls)),
    url(r'^signup/', views.sign_up),
    url(r'^get-token/', views.get_token),
    url(r'^verify-user/(?P<user_id>[\d+]+)/(?P<activation_nonce>[0-9a-z]+)/?$', views.verify_user),
]
