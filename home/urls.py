from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home_view, name='home'),
    path('work-session/', views.work_session_view, name='work_session'),
    path('download/', views.download_records, name='download')
]
