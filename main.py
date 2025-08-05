import os
import re
import time
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

# ----------------------------------------
# ユーティリティ関数
# ----------------------------------------

def extract_number_from_title(title):
    """タイトルの末尾から数字を抽出（見つからなければ -1）"""
    match = re.search(r'(\d+)$', title)
    return int(match.group(1)) if match else -1


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
    df['playlist_id'] = df['url'].apply(lambda url: url.split('list=')[1] if 'list=' in url else '')
    playlist_map = {p['playlist_id']: p['video_count'] for p in youtube_playlists}

    def update_count(row):
        return playlist_map.get(row['playlist_id'], row['count'])  # 一致するIDがなければ現状維持

    df['count'] = df.apply(update_count, axis=1)
    df.drop(columns=['playlist_id'], inplace=True)
    df.to_csv(csv_path, index=False)

    print('✅ count を更新しました')


# ----------------------------------------
# データ取得・比較処理
# ----------------------------------------

def fetch_playlist_data(playlist):
    """
    プレイリスト内の動画情報を取得し、MAIN_DATA_CSVに追記する。
    CSV列: id, title, channel, date, url, playlist
    """
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
        time.sleep(1)  # APIアクセス間隔を空ける

        for item in response['items']:
            snippet = item['snippet']
            video_id = snippet['resourceId']['videoId']
            video_title = snippet['title']
            channel_title = snippet['videoOwnerChannelTitle'] if 'videoOwnerChannelTitle' in snippet else snippet['channelTitle']
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

    # 既存データ読み込みとid付与
    if os.path.exists(MAIN_DATA_CSV):
        df_existing = pd.read_csv(MAIN_DATA_CSV)
        max_id = df_existing['id'].max() if not df_existing.empty else 0
    else:
        df_existing = pd.DataFrame()
        max_id = 0

    # 新規動画データDataFrame作成
    df_new = pd.DataFrame(videos)
    df_new.insert(0, 'id', range(max_id + 1, max_id + 1 + len(df_new)))

    # 既存と新規を結合し保存（追記）
    if not df_existing.empty:
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(MAIN_DATA_CSV, index=False)

    print(f"✅ プレイリスト『{playlist_title}』の動画データを {MAIN_DATA_CSV} に追記しました（{len(df_new)}件）")

    if os.path.exists(PLAYLISTS_CSV):
        df_playlists = pd.read_csv(PLAYLISTS_CSV)
    else:
        df_playlists = pd.DataFrame(columns=['title', 'playlist_id', 'video_count'])

    # video_count は今回取得動画数
    video_count = len(videos)

    # 既存にプレイリストがあれば更新、なければ追加
    if playlist_id in df_playlists['playlist_id'].values:
        df_playlists.loc[df_playlists['playlist_id'] == playlist_id, ['title', 'video_count']] = [playlist_title, video_count]
    else:
        df_playlists = pd.concat([df_playlists, pd.DataFrame([{
            'title': playlist_title,
            'playlist_id': playlist_id,
            'video_count': video_count
        }])], ignore_index=True)

    df_playlists.to_csv(PLAYLISTS_CSV, index=False)

    print(f"✅ プレイリスト情報を {PLAYLISTS_CSV} に更新しました")



def identify_and_fetch_target_playlists(youtube_playlists, csv_path):
    """
    CSVに存在しない、または count が一致しないプレイリストに対してデータ取得を行う
    """
    df = pd.read_csv(csv_path)
    df['playlist_id'] = df['url'].apply(lambda url: url.split('list=')[1] if 'list=' in url else '')
    csv_map = df.set_index('playlist_id').to_dict(orient='index')

    for playlist in youtube_playlists:
        pid = playlist['playlist_id']
        youtube_count = playlist['video_count']
        csv_entry = csv_map.get(pid)

        if csv_entry is None:
            print(f"🆕 CSVに存在しないプレイリスト: {playlist['title']}")
            fetch_playlist_data(playlist)
        elif youtube_count != csv_entry['count']:
            print(f"⚠️ count不一致: {playlist['title']}（CSV: {csv_entry['count']} → YouTube: {youtube_count}）")
            fetch_playlist_data(playlist)


def check_csv_latest_playlist(youtube_playlists, csv_path):
    """CSV上の最新プレイリストがYouTubeと一致するか確認"""
    df = pd.read_csv(csv_path)
    df['number'] = df['title'].apply(extract_number_from_title)
    latest_row = df.loc[df['number'].idxmax()]
    latest_title = latest_row['title']
    csv_count = latest_row['count']

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

    # 重複削除（URL基準）
    df = df.drop_duplicates(subset='url')

    # 新しい順（最新が上）に並び替え
    df = df.sort_values(by='date', ascending=False).reset_index(drop=True)

    # 既存の id 列があれば削除
    if 'id' in df.columns:
        df = df.drop(columns=['id'])

    # id を再付与（1スタート）
    df.insert(0, 'id', range(1, len(df) + 1))

    # 保存
    df.to_csv(MAIN_DATA_CSV, index=False)

    after_count = len(df)
    print(f"🧹 main-data.csv を整理しました（{before_count} → {after_count}件、最新順・重複削除）")


def filter_checked_channels(output_csv=FILTERED_DATA_CSV, verbose=True):
    """checkが1のチャンネルに該当する動画のみを抽出し、CSVに出力"""
    if not os.path.exists(MAIN_DATA_CSV) or not os.path.exists(CATEGORIZE_CSV):
        print("❌ 必要なCSVファイルが存在しません")
        return

    df_main = pd.read_csv(MAIN_DATA_CSV)
    df_categorize = pd.read_csv(CATEGORIZE_CSV)

    # check == 1 のチャンネルを抽出
    checked_channels = df_categorize[df_categorize['check'] == 1]['channel'].unique()

    # mainデータから該当チャンネルのみ抽出
    df_filtered = df_main[df_main['channel'].isin(checked_channels)]

    # 結果をCSVに出力
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


if __name__ == '__main__':
    # main()
    filter_checked_channels()
