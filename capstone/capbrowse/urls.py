from . import views
from django.urls import path

urlpatterns = [
    ### pages ###
    path('view/case/<int:case_id>/', views.view_case, name='view_case'),
    path('view/court/<int:court_id>/', views.view_court, name='view_court'),
    path('view/reporter/<int:reporter_id>/', views.view_reporter, name='view_reporter'),
    path('view/jurisdiction/<int:jurisdiction_id>/', views.view_jurisdiction, name='view_jurisdiction'),
    path('search/', views.search, name='search'),
    path('search_data/jurisdiction_list', views.jurisdiction_list, name='jurisdiction_list'),
    path('search_data/court_list', views.court_list, name='court_list'),
    path('search_data/reporter_list', views.reporter_list, name='reporter_list'),
]

