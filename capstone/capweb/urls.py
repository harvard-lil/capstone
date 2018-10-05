
from . import views
from django.contrib.auth import views as auth_views
from django.urls import path
from django.conf.urls import include
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
    path('robots.txt', TemplateView.as_view(template_name='robots.txt',
                                            content_type='text/plain'), name='robots'),

    ### bulk data ###
    path('bulk/', TemplateView.as_view(template_name='bulk_docs.html'), name='bulk-docs'),
    path('bulk/download/', user_views.bulk, name='bulk-download'),

    path('terms', TemplateView.as_view(template_name='terms-of-use.html',
                                       extra_context={'hide_footer': True}), name='terms'),
    path('privacy', TemplateView.as_view(template_name='privacy-policy.html',
                                       extra_context={'hide_footer': True}), name='privacy'),

    path('gallery/wordclouds', views.wordclouds, name='wordclouds'),
    path('gallery/limericks', views.limericks, name='limericks'),

    path('contact/',  views.contact, name='contact'),

    ### user account pages ###

    # All templates live in capapi/registration for now
    path('user/login/', auth_views.LoginView.as_view(form_class=LoginForm), name='login'),
    path('user/register/', user_views.register_user, name='register'),
    path('user/verify-user/<int:user_id>/<activation_nonce>/', user_views.verify_user, name='verify-user'),
    # override default Django login view to use custom LoginForm
    path('user/', include('django.contrib.auth.urls')),  # logout, password change, password reset
    path('user/details', user_views.user_details, name='user-details'),
    path('user/research-request', user_views.request_research_access, name='research-request'),
    path('user/research-request-success', TemplateView.as_view(template_name='research_request/research_request_success.html'), name='research-request-success'),
    path('user/resend-verification/', user_views.resend_verification, name='resend-verification'),

    path('maintenance/', views.maintenance_mode , name='maintenance_mode'),

]

