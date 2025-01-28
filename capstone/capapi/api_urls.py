from django.conf import settings
from django.urls import path, re_path, include
from django.views.generic import RedirectView, TemplateView
from rest_framework import routers

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
router.register('resolve', api_views.ResolveDocumentViewSet, basename="resolve")

unstable_router = routers.DefaultRouter()

# filter out bulk endpoint from API browser listing
class FilteredAPIRootView(routers.APIRootView):
    def get(self, request, *args, **kwargs):
        self.api_root_dict = {k:v for k,v in self.api_root_dict.items() if k != 'bulk'}
        return super().get(request, *args, **kwargs)
router.APIRootView = FilteredAPIRootView

urlpatterns = [
    path('v1/', include(router.urls)),
    path('unstable/', include(unstable_router.urls)),
    # convenience pattern: catch all citations, redirect in CaseDocumentViewSet's retrieve
    re_path(r'^v1/cases/(?P<id>[0-9A-Za-z\s\.]+)/$', api_views.CaseDocumentViewSet.as_view({'get': 'retrieve'}), name='case-get-cite'),

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