from django.conf.urls import url
from django.urls import path, re_path, include

from . import views


urlpatterns = [
    ### pages ###
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    path('tools/', views.tools, name='tools'),
]