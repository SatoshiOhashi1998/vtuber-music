# playlists/models.py
from django.db import models
from django.contrib.auth.models import User
from videos.models import Video


class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}（{self.user.username}）"


class PlaylistVideo(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='videos')
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('playlist', 'video')  # 同じプレイリストに重複登録を防ぐ
        ordering = ['order']  # デフォルト並び順

    def __str__(self):
        return f"{self.video.title} in {self.playlist.name} (order: {self.order})"
