from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.conf import settings
from django.conf.urls import url, include
from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework import routers
from capi_project import views

router = routers.DefaultRouter()
router.register(r'cases', views.CaseViewSet)
router.register(r'jurisdictions', views.JurisdictionViewSet)
router.register(r'courts', views.CourtViewSet)
router.register(r'reporters', views.ReporterViewSet)
router.register(r'accounts', views.UserViewSet)

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='docs.html'), name='docs'),
    url(r'^', include(router.urls)),
    url(r'^admin', include(admin.site.urls)),
    url(r'^accounts/verify-user/(?P<user_id>[\d+]+)/(?P<activation_nonce>[0-9a-z]+)/?$', views.verify_user),
    url(r'^cases/$', views.CaseViewSet.as_view({'get':'case_list'}), name='list-all-cases'),
    url(r'^cases/citation/(?P<citation>[\w.\d.\s+]+)?$', views.get_case_by_citation, name='get-case-by-citation'),
    url(r'^cases/jurisdictions/?$', views.list_jurisdictions, name='list-jurisdictions'),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/$', views.CaseViewSet.as_view({'get':'case_list'}), name='list-for-jurisdiction'),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/reporters/?$', views.list_reporters, name='list-reporters'),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\s\w.]+)/?$', views.CaseViewSet.as_view({'get':'case_list'})),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\s\w.]+)/volumes/?$', views.list_volumes),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\s\w.]+)/(?P<volume>[\d+]+)/?$', views.CaseViewSet.as_view({'get':'case_list'})),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\s\w.]+)/(?P<volume>[\d+]+)/(?P<firstpage>[\d+]+)/?$', views.CaseViewSet.as_view({'get':'case_list'})),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\s\w.]+)/(?P<volume>[\d+]+)/(?P<firstpage>[\d+]+)/(?P<name_abbreviation>[\w.\s+]+)?$',views.CaseViewSet.as_view({'get':'case_list'})),
    url(r'^cases/(?P<jurisdiction>[\w\s+]+)/(?P<reporter>[\d\s\w.]+)/(?P<volume>[\d+]+)/(?P<name_abbreviation>[\w.\s+]+)?$', views.CaseViewSet.as_view({'get':'case_list'})),
]
