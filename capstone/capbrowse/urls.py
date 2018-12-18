from . import views
from django.urls import path

urlpatterns = [
    ### pages ###
    path('browse/case/<int:case_id>/', views.view_case, name='view_case'),
    path('browse/court/<int:court_id>/', views.view_court, name='view_court'),
    path('browse/reporter/<int:reporter_id>/', views.view_reporter, name='view_reporter'),
    path('browse/jurisdiction/<int:jurisdiction_id>/', views.view_jurisdiction, name='view_jurisdiction'),
    path('browse/', views.browse, name='browse'),
    path('browse/jurisdiction_list', views.jurisdiction_list, name='jurisdiction_list'),
    path('browse/court_list', views.court_list, name='court_list'),
    path('browse/reporter_list', views.reporter_list, name='reporter_list'),
]

