from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('rules/', views.rules, name='rules'),
    path('data/', views.data_status, name='data'),
    path('analysis/', views.analysis, name='analysis'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('api/analysis/', views.api_analysis, name='api_analysis'),
    path('api/recommendations/', views.api_recommendations, name='api_recommendations'),
    path('api/status/', views.api_status, name='api_status'),
    path('api/cron/ingest/', views.cron_ingest, name='cron_ingest'),
]
