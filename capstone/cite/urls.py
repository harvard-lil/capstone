from django.urls import path

from . import views

urlpatterns = [
    path('robots.txt', views.robots, name='robots'),
    path('set-cookie/', views.set_cookie, name='set_cookie'),
    path('redact/<int:case_id>/', views.redact_case, name='redact_case'),
    path('pdf/<int:case_id>/<str:pdf_name>', views.case_pdf, name='case_pdf'),
    path('image/<str:series_slug>/<str:volume_number_slug>/<str:page_number>', views.page_image, name='page_image'),
    path('<str:series_slug>/<str:volume_number_slug>/<str:page_number>/<int:case_id>/', views.citation, name='citation'),
    path('<str:series_slug>/<str:volume_number_slug>/<str:page_number>/', views.citation, name='citation'),
    path('<str:series_slug>/<str:volume_number_slug>/', views.volume, name='volume'),
    path('<str:series_slug>/', views.series, name='series'),
    path('', views.home, name='cite_home'),
]