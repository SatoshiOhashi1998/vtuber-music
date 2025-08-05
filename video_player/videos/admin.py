from django.contrib import admin
from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'channel', 'date', 'playlist')  # 一覧に表示したいフィールド
    search_fields = ('title', 'channel', 'playlist')  # 管理画面で検索できるフィールド
    list_filter = ('channel', 'playlist', 'date')  # フィルタサイドバーに表示
