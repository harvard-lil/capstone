from . import views
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import TemplateView

from capapi.views import user_views
from capapi.forms import LoginForm

from capweb.helpers import safe_domains


urlpatterns = [
    ### pages ###
    path('', views.index, name='home'),
    path('gallery/', views.gallery, name='gallery'),
    path('search/', views.search, name='search'),
    path('trends/', views.trends, name='trends'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
    path('fetch/', views.fetch, name='fetch'),

    path('view/court/<int:court_id>/', views.view_court, name='view_court'),
    path('view/reporter/<int:reporter_id>/', views.view_reporter, name='view_reporter'),
    path('view/jurisdiction/<int:jurisdiction_id>/', views.view_jurisdiction, name='view_jurisdiction'),



    ### bulk data ###
    path('bulk/download/', user_views.bulk, name='bulk-download'),

    ### legacy doc urls
    path('api/', views.legacy_docs_redirect, name='api'),
    path('about/', views.legacy_docs_redirect, name='about'),
    path('tools/', views.legacy_docs_redirect, name='tools'),
    path('search-docs/', views.legacy_docs_redirect, name='search-docs'),
    path('trends-docs/', views.legacy_docs_redirect, name='trends-docs'),
    path('action/', views.legacy_docs_redirect, name='action'),
    path('action/guidelines/', views.legacy_docs_redirect, name='action-guidelines'),
    path('action/case-study-nm/', views.legacy_docs_redirect, name='action-case-study-nm'),
    path('action/case-study-ark/', views.legacy_docs_redirect, name='action-case-study-ark'),
    path('action/case-study-canada/', views.legacy_docs_redirect, name='action-case-study-canada'),
    path('bulk/', views.legacy_docs_redirect, name='bulk-docs'),

    path('terms', views.legacy_docs_redirect, name='terms'),
    path('privacy', views.legacy_docs_redirect, name='privacy'),
    path('changelog', views.legacy_docs_redirect, name='changelog'),

    ### main docs url
    re_path(r'^docs/(.*$)', views.docs, name='docs'),

    ### exhibits ###
    path('exhibits/wordclouds', views.wordclouds, name='wordclouds'),
    path('exhibits/limericks', views.limericks, name='limericks'),
    path('exhibits/witchcraft', TemplateView.as_view(template_name='gallery/witchcraft.html'), name='witchcraft'),
    path('exhibits/cite-grid', TemplateView.as_view(template_name='exhibits/cite-grid.html'), name='cite-grid'),

    ### gallery sections ###
    path('gallery/<str:section_slug>', views.gallery_section, name='gallery_section'),

    ### contact ###
    path('contact/', views.contact, name='contact'),
    path('contact-success/', TemplateView.as_view(template_name='form_success.html',
                                                  extra_context={
                                                      'form_title': 'contact',
                                                      'message': 'We\'ll be in touch shortly.'
                                                  }), name='contact-success'),

    ### admin stuff ###
    path('maintenance/', views.maintenance_mode, name='maintenance_mode'),
    path('data/<str:label>', views.snippet, name='data_snippet'),
    re_path(r'^cms_files/', include('db_file_storage.urls')),
    path('screenshot/', views.screenshot, name='screenshot'),

    ### downloads ###
    re_path(r'^download/(?P<filepath>.*)', views.download_files, name='download-files'),

    ### user account pages ###

    # All templates live in capapi/registration for now
    path('user/login/', auth_views.LoginView.as_view(form_class=LoginForm, success_url_allowed_hosts=safe_domains),
         name='login'),
    path('user/register/', user_views.register_user, name='register'),
    path('user/verify-user/<int:user_id>/<activation_nonce>/', user_views.verify_user, name='verify-user'),
    path('user/reset-api-key/', user_views.reset_api_key, name='reset-api-key'),
    # override default Django login view to use custom LoginForm
    path('user/', include('django.contrib.auth.urls')),  # logout, password change, password reset
    path('user/details', user_views.user_details, name='user-details'),
    path('user/history', user_views.user_history, name='user-history'),
    path('user/resend-verification/', user_views.resend_verification, name='resend-verification'),
    path('user/delete-account', user_views.delete_account, name='delete_account'),

    # research access requests
    path('user/research/', TemplateView.as_view(template_name='research_request/index.html'), name='research-options'),
    path('user/research/approve/', user_views.approve_research_access, name='research-approval'),
    path('user/research/affiliated/', user_views.request_affiliated_research_access,
         name='affiliated-research-request'),
    path('user/research/affiliated-success/',
         TemplateView.as_view(template_name='research_request/affiliated_research_request_success.html'),
         name='affiliated-research-request-success'),
    path('user/research/unaffiliated/', user_views.request_unaffiliated_research_access,
         name='unaffiliated-research-request'),
    path('user/research/unaffiliated-success/',
         TemplateView.as_view(template_name='research_request/unaffiliated_research_request_success.html'),
         name='unaffiliated-research-request-success'),
    path('user/research/harvard-intro/', user_views.request_harvard_research_access_intro,
         name='harvard-research-request-intro'),
    path('user/research/non-harvard-email/',
         TemplateView.as_view(template_name='research_request/non_harvard_email.html'), name='non-harvard-email'),
    path('user/research/harvard/', user_views.request_harvard_research_access, name='harvard-research-request'),
    path('user/research/harvard-success/',
         TemplateView.as_view(template_name='research_request/harvard_research_request_success.html'),
         name='harvard-research-request-success'),
]

if settings.DEBUG:
    # debugging routes to see error pages
    # for example, http://case.test:8000/404.html shows 404 page
    urlpatterns += [
        path(error_page, TemplateView.as_view(template_name=error_page), name=error_page)
        for error_page in ('400.html', '403.html', '403_csrf.html', '404.html', '500.html', '503.html')
    ]

