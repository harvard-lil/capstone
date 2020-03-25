from django.conf import settings
from django.urls import path, re_path, include
from django.views.generic import RedirectView, TemplateView
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from capapi.views import api_views

router = routers.DefaultRouter()
router.register('cases', api_views.CaseDocumentViewSet, basename="cases")
router.register('jurisdictions', api_views.JurisdictionViewSet)
router.register('courts', api_views.CourtViewSet)
router.register('volumes', api_views.VolumeViewSet)
router.register('reporters', api_views.ReporterViewSet)
router.register('bulk', api_views.CaseExportViewSet)
router.register('ngrams', api_views.NgramViewSet, basename='ngrams')
router.register('user_history', api_views.UserHistoryViewSet)
router.register('citations', api_views.ExtractedCitationViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="CAP API",
        default_version='v1',
        description="United States Caselaw",
        terms_of_service="https://%s/terms" % settings.PARENT_HOST,
        contact=openapi.Contact(url="https://%s/contact" % settings.PARENT_HOST),
    ),
    urlconf='capapi.api_urls',
    validators=['flex', 'ssv'],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('v1/', include(router.urls)),
    # convenience pattern: catch all citations, redirect in CaseDocumentViewSet's retrieve
    re_path(r'^v1/cases/(?P<id>[0-9A-Za-z\s\.]+)/$', api_views.CaseDocumentViewSet.as_view({'get': 'retrieve'}), name='case-get-cite'),

    ### Swagger/OpenAPI/ReDoc ###
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=None), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=None), name='schema-redoc'),

    path('robots.txt', TemplateView.as_view(template_name='robots_api.txt', content_type='text/plain'), name='robots_api'),
    path('', RedirectView.as_view(url='/v1/', permanent=False), name='api-root')
]

# use django-debug-toolbar if installed
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass