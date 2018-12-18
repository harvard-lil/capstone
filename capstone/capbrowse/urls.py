from . import views
from django.urls import path

urlpatterns = [
    ### pages ###
    path('search/case/<int:case_id>/', views.view_case, name='view_case'),
    path('search/court/<int:court_id>/', views.view_court, name='view_court'),
    path('search/reporter/<int:reporter_id>/', views.view_reporter, name='view_reporter'),
    path('search/jurisdiction/<int:jurisdiction_id>/', views.view_jurisdiction, name='view_jurisdiction'),
    path('search/', views.search, name='search'),
    path('search/jurisdiction_list', views.jurisdiction_list, name='jurisdiction_list'),
    path('search/court_list', views.court_list, name='court_list'),
    path('search/reporter_list', views.reporter_list, name='reporter_list'),
]

