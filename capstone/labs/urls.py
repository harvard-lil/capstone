from . import views
from django.urls import path

from .views import LabMarkdownView
from django.conf import settings

# General labs URLS — No project specific stuff
urlpatterns = [
    path('', LabMarkdownView.as_view(template_name='labs-about.md'), name='labs'),
]

# Project URLs- make discreet groups of URLs for each project

if settings.LABS:
    # # # # chronolawgic # # # #
    urlpatterns += [
        path('chronolawgic/', LabMarkdownView.as_view(template_name='lab/chronolawgic/about-chronolawgic.md'),
             name='chronolawgic'),
        path('chronolawgic/timeline/', views.chronolawgic, name='chronolawgic-dashboard'),
        # your timeline list, create, delete
        path('chronolawgic/api/create', views.chronolawgic_api_create, name='chronolawgic-api-create'),
        path('chronolawgic/api/retrieve/:timeline_id', views.chronolawgic_api_retrieve, name='chronolawgic-api-retrieve'),
        path('chronolawgic/api/update/:timeline_id', views.chronolawgic_api_update, name='chronolawgic-api-update'),
        path('chronolawgic/api/delete/:timeline_id', views.chronolawgic_api_delete, name='chronolawgic-api-delete')
    ]