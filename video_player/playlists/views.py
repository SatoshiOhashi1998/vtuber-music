from django.shortcuts import render, redirect, get_object_or_404
from .models import Playlist, PlaylistVideo
from .forms import PlaylistForm, PlaylistVideoOrderForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from urllib.parse import urlparse, parse_qs


@login_required
def playlist_list(request):
    playlists = Playlist.objects.filter(user=request.user).order_by('name')

    # 新規作成
    if request.method == 'POST' and 'create' in request.POST:
        form = PlaylistForm(request.POST)
        if form.is_valid():
            new_playlist = form.save(commit=False)
            new_playlist.user = request.user
            new_playlist.save()
            return redirect('playlists_list')
    else:
        form = PlaylistForm()

    return render(request, 'playlists/playlist_list.html', {
        'playlists': playlists,
        'form': form
    })


@login_required
def playlist_edit(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PlaylistForm(request.POST, instance=playlist)
        if form.is_valid():
            form.save()
    return redirect('playlists_list')


@login_required
def playlist_delete(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    playlist.delete()
    return redirect('playlists_list')


@login_required
def playlist_detail(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    videos = playlist.videos.all()

    if request.method == 'POST':
        # 並び替えと名前変更
        for pv in videos:
            field_name = f'order_{pv.id}'
            if field_name in request.POST:
                try:
                    pv.order = int(request.POST[field_name])
                    pv.save()
                except ValueError:
                    pass  # 無視
        if 'rename' in request.POST:
            playlist.name = request.POST.get('name', playlist.name)
            playlist.save()

        return redirect('playlist_detail', pk=pk)

    return render(request, 'playlists/playlist_detail.html', {
        'playlist': playlist,
        'videos': videos,
    })


@csrf_exempt
@login_required
def playlist_reorder(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for item in data:
                pv = PlaylistVideo.objects.get(pk=item['id'], playlist=playlist)
                pv.order = item['order']
                pv.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


@csrf_exempt
@login_required
def playlist_video_remove(request, pk):
    if request.method == 'POST':
        pv = get_object_or_404(PlaylistVideo, pk=pk, playlist__user=request.user)
        pv.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


@login_required
def playlist_play(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    videos = playlist.videos.all()

    # URLからYouTubeの動画IDを取り出す関数
    def extract_youtube_id(url):
        parsed_url = urlparse(url)
        if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
            qs = parse_qs(parsed_url.query)
            return qs.get('v', [None])[0]
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
        return None

    video_list = []
    for pv in videos:
        video_id = extract_youtube_id(pv.video.url)
        if video_id:
            video_list.append({
                'title': pv.video.title,
                'video_id': video_id,
                'pk': pv.video.pk,
            })

    # 再生開始動画指定用（クエリパラメータ）
    start_video_id = request.GET.get('start_video')
    start_index = 0
    if start_video_id:
        for idx, video in enumerate(video_list):
            if str(video['pk']) == start_video_id:
                start_index = idx
                break

    return render(request, 'playlists/playlist_play.html', {
        'playlist': playlist,
        'videos': video_list,
        'start_index': start_index,
    })
