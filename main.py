import os
import re
import time
import shutil
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_ID = os.getenv('CHANNEL_ID')
PLAYLISTS_CSV = os.getenv('PLAYLISTS_CSV')
MAIN_DATA_CSV = os.getenv('MAIN_DATA_CSV')
CATEGORIZE_CSV = os.getenv('CATEGORIZE_CSV')
FILTERED_DATA_CSV = os.getenv('FILTERED_DATA_CSV')
OUTPUT_PATH = os.getenv('OUTPUT_PATH')

# ----------------------------------------
# ユーティリティ関数
# ----------------------------------------

def extract_number_from_title(title):
    """タイトルの末尾から数字を抽出（見つからなければ -1）"""
    match = re.search(r'(\d+)$', title)
    return int(match.group(1)) if match else -1

def normalize_playlist_id(pid):
    """URLからplaylist IDを抽出、すでにID形式ならそのまま"""
    return pid.split('list=')[1] if isinstance(pid, str) and 'list=' in pid else pid

def to_playlist_url(playlist_id):
    """playlist IDからURLを生成"""
    return f"https://www.youtube.com/playlist?list={playlist_id}"

# ----------------------------------------
# YouTube API 操作
# ----------------------------------------

def get_playlists(api_key, channel_id):
    """YouTube APIからプレイリスト一覧を取得"""
    youtube = build('youtube', 'v3', developerKey=api_key)
    playlists = []
    nextPageToken = None

    while True:
        request = youtube.playlists().list(
            part='snippet,contentDetails',
            channelId=channel_id,
            maxResults=50,
            pageToken=nextPageToken
        )
        response = request.execute()

        for item in response['items']:
            playlists.append({
                'title': item['snippet']['title'],
                'playlist_id': item['id'],
                'video_count': item['contentDetails']['itemCount']
            })

        nextPageToken = response.get('nextPageToken')
        if not nextPageToken:
            break

    return playlists

# ----------------------------------------
# CSV操作
# ----------------------------------------

def update_csv_counts(csv_path, youtube_playlists):
    """CSV内のcount列をYouTube上の実数で更新"""
    df = pd.read_csv(csv_path)
    df['playlist_id'] = df['url'].apply(normalize_playlist_id)
    playlist_map = {p['playlist_id']: p['video_count'] for p in youtube_playlists}

    def update_count(row):
        return playlist_map.get(row['playlist_id'], row['count'])

    df['count'] = df.apply(update_count, axis=1)
    df.drop(columns=['playlist_id'], inplace=True)
    df.to_csv(csv_path, index=False)

    print('✅ count を更新しました')

# ----------------------------------------
# データ取得・比較処理
# ----------------------------------------

def fetch_playlist_data(playlist):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    playlist_id = playlist['playlist_id']
    playlist_title = playlist['title']

    videos = []
    nextPageToken = None
    while True:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=nextPageToken
        )
        response = request.execute()
        time.sleep(1)

        for item in response['items']:
            snippet = item['snippet']
            video_id = snippet['resourceId']['videoId']
            video_title = snippet['title']
            channel_title = snippet.get('videoOwnerChannelTitle', snippet.get('channelTitle', ''))
            published_at = snippet['publishedAt']
            video_url = f'https://www.youtube.com/watch?v={video_id}'

            videos.append({
                'title': video_title,
                'channel': channel_title,
                'date': published_at,
                'url': video_url,
                'playlist': playlist_title
            })

        nextPageToken = response.get('nextPageToken')
        if not nextPageToken:
            break

    if os.path.exists(MAIN_DATA_CSV):
        df_existing = pd.read_csv(MAIN_DATA_CSV)
        max_id = df_existing['id'].max() if not df_existing.empty else 0
    else:
        df_existing = pd.DataFrame()
        max_id = 0

    df_new = pd.DataFrame(videos)
    df_new.insert(0, 'id', range(max_id + 1, max_id + 1 + len(df_new)))

    df_combined = pd.concat([df_existing, df_new], ignore_index=True) if not df_existing.empty else df_new
    df_combined.to_csv(MAIN_DATA_CSV, index=False)

    print(f"✅ プレイリスト『{playlist_title}』の動画データを {MAIN_DATA_CSV} に追記しました（{len(df_new)}件）")

    if os.path.exists(PLAYLISTS_CSV):
        df_playlists = pd.read_csv(PLAYLISTS_CSV)
        df_playlists['playlist_id'] = df_playlists['playlist_id'].apply(normalize_playlist_id)
    else:
        df_playlists = pd.DataFrame(columns=['title', 'playlist_id', 'video_count'])

    video_count = len(videos)

    if playlist_id in df_playlists['playlist_id'].values:
        df_playlists.loc[df_playlists['playlist_id'] == playlist_id, ['title', 'video_count']] = [playlist_title, video_count]
    else:
        df_playlists = pd.concat([df_playlists, pd.DataFrame([{
            'title': playlist_title,
            'playlist_id': playlist_id,
            'video_count': video_count
        }])], ignore_index=True)

    # ✅ 保存前に playlist_id を URL形式に戻す
    df_playlists['playlist_id'] = df_playlists['playlist_id'].apply(to_playlist_url)
    df_playlists.to_csv(PLAYLISTS_CSV, index=False)

    print(f"✅ プレイリスト情報を {PLAYLISTS_CSV} に更新しました")

def identify_and_fetch_target_playlists(youtube_playlists, csv_path):
    df = pd.read_csv(csv_path)
    df['playlist_id'] = df['playlist_id'].apply(normalize_playlist_id)
    csv_map = df.set_index('playlist_id').to_dict(orient='index')

    for playlist in youtube_playlists:
        pid = playlist['playlist_id']
        youtube_count = playlist['video_count']
        csv_entry = csv_map.get(pid)

        if csv_entry is None:
            print(f"🆕 CSVに存在しないプレイリスト: {playlist['title']}")
            fetch_playlist_data(playlist)
        elif youtube_count != csv_entry['video_count']:
            print(f"⚠️ count不一致: {playlist['title']}（CSV: {csv_entry['video_count']} → YouTube: {youtube_count}）")
            fetch_playlist_data(playlist)

def check_csv_latest_playlist(youtube_playlists, csv_path):
    df = pd.read_csv(csv_path)
    df['playlist_id'] = df['playlist_id'].apply(normalize_playlist_id)
    df['number'] = df['title'].apply(extract_number_from_title)
    latest_row = df.loc[df['number'].idxmax()]
    latest_title = latest_row['title']
    csv_count = latest_row['video_count']

    print(f"🗂️ CSV上の最新プレイリスト: {latest_title}（count: {csv_count}）")

    match = next((p for p in youtube_playlists if p['title'] == latest_title), None)
    if not match:
        print('⚠️ YouTube上に同名のプレイリストが見つかりません')
        return

    youtube_count = match['video_count']
    if csv_count == youtube_count:
        print('✅ CSVとYouTubeの動画数は一致しています')
    else:
        print(f'❌ 不一致です（CSV: {csv_count}, YouTube: {youtube_count}）')

def clean_and_sort_main_data():
    if not os.path.exists(MAIN_DATA_CSV):
        print(f"❌ {MAIN_DATA_CSV} が存在しません")
        return

    df = pd.read_csv(MAIN_DATA_CSV)
    before_count = len(df)
    df = df.drop_duplicates(subset='url')
    df = df.sort_values(by='date', ascending=False).reset_index(drop=True)

    if 'id' in df.columns:
        df = df.drop(columns=['id'])

    df.insert(0, 'id', range(1, len(df) + 1))
    df.to_csv(MAIN_DATA_CSV, index=False)
    after_count = len(df)

    print(f"🧹 main-data.csv を整理しました（{before_count} → {after_count}件、最新順・重複削除）")

def filter_checked_channels(output_csv=FILTERED_DATA_CSV, verbose=True):
    if not os.path.exists(MAIN_DATA_CSV) or not os.path.exists(CATEGORIZE_CSV):
        print("❌ 必要なCSVファイルが存在しません")
        return

    df_main = pd.read_csv(MAIN_DATA_CSV)
    df_categorize = pd.read_csv(CATEGORIZE_CSV)
    checked_channels = df_categorize[df_categorize['check'] == 1]['channel'].unique()
    df_filtered = df_main[df_main['channel'].isin(checked_channels)]
    df_filtered.to_csv(output_csv, index=False)

    if verbose:
        print(f"✅ check=1 のチャンネルの動画を {output_csv} に保存しました（{len(df_filtered)}件）")

    return df_filtered

# ----------------------------------------
# メイン処理
# ----------------------------------------

def main():
    print('▶️ プレイリスト取得中...')
    playlists = get_playlists(API_KEY, CHANNEL_ID)

    print('🔍 CSVとの比較・データ取得対象を判定中...')
    identify_and_fetch_target_playlists(playlists, PLAYLISTS_CSV)

    clean_and_sort_main_data()
    filter_checked_channels()

    try:
        shutil.copy(FILTERED_DATA_CSV, OUTPUT_PATH)
        print(f"✅ {FILTERED_DATA_CSV} を {OUTPUT_PATH} にコピーしました。")
    except Exception as e:
        print(f"❌ コピーに失敗しました: {e}")

if __name__ == '__main__':
    main()
