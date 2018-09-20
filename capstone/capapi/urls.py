from django.urls import path, re_path, include
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from capapi.views import api_views, viz_views


router = routers.DefaultRouter()
router.register('cases', api_views.CaseViewSet)
router.register('citations', api_views.CitationViewSet)
router.register('jurisdictions', api_views.JurisdictionViewSet)
router.register('courts', api_views.CourtViewSet)
router.register('volumes', api_views.VolumeViewSet)
router.register('reporters', api_views.ReporterViewSet)
router.register('bulk', api_views.CaseExportViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="CAP API",
        default_version='v1',
        description="United States Caselaw",
        terms_of_service="https://capapi.org/terms",
        contact=openapi.Contact(email="lil@law.harvard.edu"),
    ),
    validators=['flex', 'ssv'],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    ### pages ###

    ### api ###
    path('api/v1/', include(router.urls)),
    # convenience pattern: catch all citations, redirect in CaseViewSet's retrieve
    re_path(r'^api/v1/cases/(?P<id>[0-9A-Za-z\s\.]+)/$', api_views.CaseViewSet.as_view({'get': 'retrieve'}), name='casemetadata-get-cite'),

    ### data views ###
    path('data/', viz_views.totals_view, name='totals_view'),
    path('data/details/', viz_views.details_view, name='details_view'),
    path('data/details/<str:slug>', viz_views.get_details, name='get_details'),

    ### Swagger/OpenAPI/ReDoc ###
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=None), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=None), name='schema-redoc'),

]
