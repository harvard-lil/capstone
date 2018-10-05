from django.urls import path
from capapi.views import viz_views


urlpatterns = [
    ### data views ###
    path('data/', viz_views.totals_view, name='totals_view'),
    path('data/details/', viz_views.details_view, name='details_view'),
    path('data/details/<str:slug>', viz_views.get_details, name='get_details'),
]
