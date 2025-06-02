from django.urls import path
from . import views

app_name = 'crawler'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('messages/', views.message_list, name='message_list'),
    path('channels/', views.channel_list, name='channel_list'),
    path('archived-urls/', views.archived_url_list, name='archived_url_list'),
    path('logs/', views.log_list, name='log_list'),
    path('settings/', views.settings_view, name='settings'),
    path('api/start-crawler/', views.start_crawler, name='start_crawler'),
    path('api/stop-crawler/', views.stop_crawler, name='stop_crawler'),
    path('api/crawler-status/', views.crawler_status_api, name='crawler_status_api'),
    path('api/keywords/', views.keywords_api, name='keywords_api'),
    path('api/keywords/add/', views.add_keyword_api, name='add_keyword_api'),
    path('api/keywords/toggle/', views.toggle_keyword_api, name='toggle_keyword_api'),
    path('api/keywords/delete/', views.delete_keyword_api, name='delete_keyword_api'),
    path('channels/<int:channel_id>/export-pdf/', views.export_channel_pdf, name='export_channel_pdf'),
]
