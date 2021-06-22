from . import views
from django.urls import path, re_path

from .views import LabMarkdownView
from django.conf import settings

# General labs URLS — No project specific stuff
urlpatterns = [
    path('', LabMarkdownView.as_view(template_name='labs-about.md'), name='labs'),
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

        path('chronolawgic/api/case/add-update/<str:timeline_uuid>', views.chronolawgic_add_update_case, name='chronolawgic-api-add-update-case'),
        path('chronolawgic/api/case/delete/<str:timeline_uuid>/<str:case_uuid>', views.chronolawgic_delete_case, name='chronolawgic-api-delete-case'),

        path('chronolawgic/api/event/delete/<str:timeline_uuid>', views.chronolawgic_add_update_event, name='chronolawgic-api-add-update-event'),
        path('chronolawgic/api/event/delete/<str:timeline_uuid>/<str:event_uuid>', views.chronolawgic_delete_event, name='chronolawgic-api-delete-event'),

        path('chronolawgic/api/category/add-update/<str:timeline_uuid>', views.chronolawgic_add_update_category, name='chronolawgic-api-add-update-category'),
        path('chronolawgic/api/category/delete/<str:timeline_uuid>/<str:category_uuid>', views.chronolawgic_delete_category, name='chronolawgic-api-delete-category'),


        path('chronolawgic/api/delete/<str:timeline_uuid>', views.chronolawgic_api_delete, name='chronolawgic-api-delete'),

        path('chronolawgic/api/update/<str:timeline_uuid>', views.legacy_please_refresh,
             name='chronolawgic-api-update'),
        path('chronolawgic/api/update_admin/<str:timeline_uuid>', views.legacy_please_refresh,
             name='chronolawgic-api-update-admin'),
    ]