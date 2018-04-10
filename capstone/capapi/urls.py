from django.conf.urls import url, include
from django.views.generic import TemplateView
from rest_framework import routers

from capapi import views

router = routers.DefaultRouter()
router.register(r'cases', views.CaseViewSet)
router.register(r'citations', views.CitationViewSet)
router.register(r'jurisdictions', views.JurisdictionViewSet)
router.register(r'courts', views.CourtViewSet)
router.register(r'volumes', views.VolumeViewSet)
router.register(r'reporters', views.ReporterViewSet)

user_router = routers.DefaultRouter()
user_router.register(r'accounts', views.UserViewSet)

urlpatterns = [
    url(r'^$', views.get_docs, name='docs'),
    url(r'^terms$', views.get_terms, name='terms'),
    url(r'^robots.txt$', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
    url(r'^', include(user_router.urls)),
    url(r'^api/v1/', include(router.urls)),
    # convenience pattern: catch all citations, redirect in CaseViewSet's retrieve
    url(r'^api/v1/cases/(?P<id>[0-9A-Za-z\s\.]+)/$', views.CaseViewSet.as_view({'get': 'retrieve'}), name='casemetadata-get-cite'),
    url(r'^accounts/verify-user/(?P<user_id>[\d+]+)/(?P<activation_nonce>[0-9a-z]+)/?$', views.verify_user),
]

handler404 = 'views.not_found'
