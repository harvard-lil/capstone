from . import views
from django.urls import path, re_path

from .views import LabMarkdownView
from django.conf import settings

# General labs URLS — No project specific stuff
urlpatterns = [
    path('', LabMarkdownView.as_view(template_name='labs-about.md'), name='labs'),
    path('most-cited/', views.most_cited, name='most-cited'),
    path('most-cited/data/<int:year>', views.most_cited_data, name='most-cited-data'),
    path('most-cited/overall-data/<int:year>', views.most_cited_overall, name='most-cited-overall')
]

# Project URLs- make discreet groups of URLs for each project

if 'chronolawgic' not in settings.LABS_HIDDEN:
    # # # # chronolawgic # # # #
    urlpatterns += [
        path('chronolawgic/', views.chronolawgic_redirect, name='chronolawgic'),
        re_path('chronolawgic/timeline/*', views.chronolawgic, name='chronolawgic-dashboard'),
        # your timeline list, create, delete
        path('chronolawgic/api/create/', views.chronolawgic_api_create, name='chronolawgic-api-create'),
        # create timeline from h2o url
        path('chronolawgic/api/create/h2o', views.h2o_import, name='chronolawgic-api-create-h2o'),
        path('chronolawgic/api/retrieve/', views.chronolawgic_api_retrieve, name='chronolawgic-api-retrieve'),
        path('chronolawgic/api/retrieve/<str:timeline_uuid>', views.chronolawgic_api_retrieve, name='chronolawgic-api-retrieve'),

        path('chronolawgic/api/add-update/<str:timeline_uuid>/categories',
             views.chronolawgic_update_categories, name='chronolawgic-api-update-categories'),
        path('chronolawgic/api/add-update/<str:timeline_uuid>/<str:subobject_type>',
             views.chronolawgic_add_update_subobject, name='chronolawgic-api-add-update-subobject'),
        path('chronolawgic/api/delete/<str:timeline_uuid>/<str:subobject_type>/<str:subobject_uuid>',
             views.chronolawgic_delete_subobject, name='chronolawgic-delete-subobject'),
        path('chronolawgic/api/delete/<str:timeline_uuid>', views.chronolawgic_api_delete, name='chronolawgic-api-delete'),

        path('chronolawgic/api/update/<str:timeline_uuid>/metadata', views.chronolawgic_update_timeline_metadata,
             name='chronolawgic-update-timeline-metadata'),

        path('chronolawgic/api/update/<str:timeline_uuid>', views.legacy_please_refresh,
             name='chronolawgic-api-update'),
        path('chronolawgic/api/update_admin/<str:timeline_uuid>', views.legacy_please_refresh,
             name='chronolawgic-api-update-admin'),
    ]