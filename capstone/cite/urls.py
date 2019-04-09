from django.conf import settings
from django.urls import path

from . import views

if settings.CITE_SUBDOMAIN_FEATURE:
    urlpatterns = [
        path('set-cookie/', views.set_cookie, name='set_cookie'),
        path('<str:series_slug>/<str:volume_number>/<str:page_number>/<int:case_id>', views.citation, name='citation'),
        path('<str:series_slug>/<str:volume_number>/<str:page_number>/', views.citation, name='citation'),
        path('<str:series_slug>/<str:volume_number>/', views.volume, name='volume'),
        path('<str:series_slug>/', views.series, name='series'),
        path('', views.home, name='home'),
    ]
else:
    urlpatterns = []