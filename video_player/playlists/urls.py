from django.urls import path
from . import views

urlpatterns = [
    path('', views.playlist_list, name='playlists_list'),  # プレイリスト一覧
    path('<int:pk>/', views.playlist_detail, name='playlist_detail'),  # プレイリスト詳細
    path('<int:pk>/edit/', views.playlist_edit, name='playlist_edit'),
    path('<int:pk>/delete/', views.playlist_delete, name='playlist_delete'),
    path('<int:pk>/reorder/', views.playlist_reorder, name='playlist_reorder'),  # 並び替え保存
    path('video/<int:pk>/remove/', views.playlist_video_remove, name='playlist_video_remove'),  # 削除
    path('playlists/<int:pk>/play/', views.playlist_play, name='playlist_play'),
]
