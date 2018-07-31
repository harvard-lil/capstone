from django.conf.urls import url
from django.urls import path, re_path, include

from . import views


urlpatterns = [
    ### pages ###
    path('', views.index, name='home'),
]