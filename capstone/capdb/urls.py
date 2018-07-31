from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^capdb/', views.index, name='index'),

]