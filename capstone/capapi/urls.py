from django.urls import path
from django.views.generic import TemplateView

from capapi.views import viz_views


urlpatterns = [
    ### pages ###
    # path('', doc_views.home, name='home'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),

    ### data views ###
    path('data/', viz_views.totals_view, name='totals_view'),
    path('data/details/', viz_views.details_view, name='details_view'),
    path('data/details/<str:slug>', viz_views.get_details, name='get_details'),
]
