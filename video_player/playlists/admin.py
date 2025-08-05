from django.contrib import admin
from .models import Playlist, PlaylistVideo
from videos.models import Video


class PlaylistVideoInline(admin.TabularInline):
    model = PlaylistVideo
    extra = 1  # 空のフォームを何個表示するか
    autocomplete_fields = ['video']
    ordering = ['order']


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
    inlines = [PlaylistVideoInline]
