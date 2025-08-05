from django.urls import path
from . import views

urlpatterns = [
    path('', views.video_search, name='search'),
    path('search/', views.video_search, name='video_search'),
    path('video/<int:pk>/', views.video_player, name='video_player'),
    path('video/<int:pk>/add/', views.ajax_add_to_playlist, name='ajax_add_to_playlist'),
]
