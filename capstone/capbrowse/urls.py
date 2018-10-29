from . import views
from django.urls import path

urlpatterns = [
    ### pages ###
    path('browse/case/<int:case_id>/', views.browse_case, name='browse_case'),
    path('browse/', views.browse, name='browse'),
    path('browse/jurisdiction_list', views.jurisdiction_list, name='jurisdiction_list'),
    path('browse/court_list', views.court_list, name='court_list'),
    path('browse/reporter_list', views.reporter_list, name='reporter_list'),
]

