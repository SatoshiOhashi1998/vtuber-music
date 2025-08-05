from .models import Video
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from playlists.models import Playlist, PlaylistVideo
from django.views.decorators.http import require_POST
from django.db import models


def video_player(request, pk):
    video = get_object_or_404(Video, pk=pk)
    user_playlists = []
    if request.user.is_authenticated:
        user_playlists = Playlist.objects.filter(user=request.user)
    return render(request, 'videos/player.html', {
        'video': video,
        'user_playlists': user_playlists,
    })


def video_search(request):
    query = Q()
    title = request.GET.get('title', '')
    channel = request.GET.get('channel', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    if title:
        query &= Q(title__icontains=title)
    if channel:
        query &= Q(channel__icontains=channel)
    if start_date:
        query &= Q(date__gte=start_date)
    if end_date:
        query &= Q(date__lte=end_date)

    videos = Video.objects.filter(query).order_by('-date')
    paginator = Paginator(videos, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    channels = Video.objects.values_list('channel', flat=True).distinct()

    user_playlists = []
    if request.user.is_authenticated:
        user_playlists = Playlist.objects.filter(user=request.user)

    return render(request, 'videos/search.html', {
        'page_obj': page_obj,
        'channels': channels,
        'user_playlists': user_playlists,
    })


@login_required
@require_POST
def ajax_add_to_playlist(request, pk):
    playlist_id = request.POST.get('playlist_id')
    video = get_object_or_404(Video, pk=pk)
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)

    if PlaylistVideo.objects.filter(playlist=playlist, video=video).exists():
        return JsonResponse({'success': False, 'message': 'この動画はすでにプレイリストに追加されています。'})

    max_order = playlist.videos.aggregate(max_order=models.Max('order'))['max_order'] or 0
    PlaylistVideo.objects.create(playlist=playlist, video=video, order=max_order + 1)

    return JsonResponse({'success': True, 'message': f'動画「{video.title}」をプレイリスト「{playlist.name}」に追加しました。'})
