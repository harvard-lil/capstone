from capweb.views import MarkdownView
from . import views
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import TemplateView

from capapi.views import user_views
from capapi.forms import LoginForm



urlpatterns = [
    ### pages ###
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    path('tools/', views.tools, name='tools'),
    path('gallery/', views.gallery, name='gallery'),
    path('api/', views.api, name='api'),
    path('search-docs/', MarkdownView.as_view(template_name='search_docs.md'), name='search-docs'),
    path('trends-docs/', MarkdownView.as_view(template_name='trends_docs.md'), name='trends-docs'),
    path('action/', MarkdownView.as_view(template_name='action/index.md'), name='action'),
    path('action/guidelines/', MarkdownView.as_view(template_name='action/guidelines.md'), name='action-guidelines'),
    path('action/case-study-nm/', MarkdownView.as_view(template_name='action/case-study-nm.md'), name='action-case-study-nm'),
    path('action/case-study-ark/', MarkdownView.as_view(template_name='action/case-study-ark.md'), name='action-case-study-ark'),
    path('action/case-study-canada/', MarkdownView.as_view(template_name='action/case-study-canada.md'), name='action-case-study-canada'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt',
                                            content_type='text/plain'), name='robots'),

    ### bulk data ###
    path('bulk/download/', user_views.bulk, name='bulk-download'),
    path('bulk/', MarkdownView.as_view(template_name='bulk_docs.md'), name='bulk-docs'),

    path('terms', MarkdownView.as_view(template_name='terms-of-use.md'), name='terms'),
    path('privacy', MarkdownView.as_view(template_name='privacy-policy.md'), name='privacy'),
    path('changelog', MarkdownView.as_view(template_name='changelog.md'), name='changelog'),

    path('gallery/wordclouds', views.wordclouds, name='wordclouds'),
    path('gallery/limericks', views.limericks, name='limericks'),
    path('gallery/witchcraft', TemplateView.as_view(template_name='gallery/witchcraft.html'), name='witchcraft'),

    path('contact/', views.contact, name='contact'),
    path('contact-success/', TemplateView.as_view(template_name='form_success.html',
                                                  extra_context={
                                                      'form_title': 'contact',
                                                      'message': 'We\'ll be in touch, shortly.'
                                                  }),  name='contact-success'),
    ### downloads ###
    path('download', views.download_files, name='download-files'),
    re_path(r'download/(?P<filepath>.*)', views.download_files, name='download-files-in-path'),
    path('download_contents', views.download_contents_file, name='download-contents'),

    ### user account pages ###

    # All templates live in capapi/registration for now
    path('user/login/', auth_views.LoginView.as_view(form_class=LoginForm), name='login'),
    path('user/register/', user_views.register_user, name='register'),
    path('user/verify-user/<int:user_id>/<activation_nonce>/', user_views.verify_user, name='verify-user'),
    path('user/reset-api-key/', user_views.reset_api_key, name='reset-api-key'),
    # override default Django login view to use custom LoginForm
    path('user/', include('django.contrib.auth.urls')),  # logout, password change, password reset
    path('user/details', user_views.user_details, name='user-details'),
    path('user/resend-verification/', user_views.resend_verification, name='resend-verification'),
    path('user/delete-account', user_views.delete_account, name='delete_account'),
    # research access requests
    ]+([
        path('user/research/', TemplateView.as_view(template_name='research_request/index.html', extra_context={'HARVARD_RESEARCHER_FEATURE': settings.HARVARD_RESEARCHER_FEATURE}), name='research-options'),
        path('user/research/approve/', user_views.approve_research_access, name='research-approval'),
        path('user/research/affiliated/', user_views.request_affiliated_research_access, name='affiliated-research-request'),
        path('user/research/affiliated-success/', TemplateView.as_view(template_name='research_request/affiliated_research_request_success.html'), name='affiliated-research-request-success'),
        path('user/research/unaffiliated/', user_views.request_unaffiliated_research_access, name='unaffiliated-research-request'),
        path('user/research/unaffiliated-success/', TemplateView.as_view(template_name='research_request/unaffiliated_research_request_success.html'), name='unaffiliated-research-request-success'),
        ]+([
            path('user/research/harvard-intro/', user_views.request_harvard_research_access_intro, name='harvard-research-request-intro'),
            path('user/research/non-harvard-email/', TemplateView.as_view(template_name='research_request/non_harvard_email.html'), name='non-harvard-email'),
            path('user/research/harvard/', user_views.request_harvard_research_access, name='harvard-research-request'),
            path('user/research/harvard-success/', TemplateView.as_view(template_name='research_request/harvard_research_request_success.html'), name='harvard-research-request-success'),
        ] if settings.HARVARD_RESEARCHER_FEATURE else [])+[
    ] if settings.NEW_RESEARCHER_FEATURE else [
        path('user/research/', user_views.request_legacy_research_access, name='unaffiliated-research-request'),
        path('user/research/success/', TemplateView.as_view(template_name='research_request/unaffiliated_research_request_success.html'), name='unaffiliated-research-request-success'),
    ])+[

    ### admin stuff ###
    path('maintenance/', views.maintenance_mode , name='maintenance_mode'),
    path('data/<str:label>', views.snippet, name='data_snippet'),
    re_path(r'^cms_files/', include('db_file_storage.urls')),
    path('screenshot/', views.screenshot, name='screenshot'),
]

if settings.DEBUG:
    # debugging routes to see error pages
    # for example, https://case.test:8000/404.html shows 404 page
    urlpatterns += [
        path(error_page, TemplateView.as_view(template_name=error_page), name=error_page)
        for error_page in ('400.html', '403.html', '403_csrf.html', '404.html', '500.html', '503.html')
    ]

