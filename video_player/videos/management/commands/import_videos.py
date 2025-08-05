from django.core.management.base import BaseCommand
from videos.models import Video
from datetime import datetime
import csv


class Command(BaseCommand):
    help = 'CSVファイルからVideoデータをインポートします（重複URLはスキップ）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file', type=str,
            default=r'C:\Users\user\PycharmProjects\MyUtilProject\MyApp\vtuber-music\video_player\videos\data\filtered_data.csv', help='CSVファイルへのパス'
            )

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        videos = []

        existing_urls = set(Video.objects.values_list('url', flat=True))

        def parse_date_flexibly(date_str):
            formats = [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y/%m/%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            raise ValueError(f"time data '{date_str}' does not match known formats")

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    url = row['url'].strip()

                    if url in existing_urls:
                        self.stderr.write(f"スキップ（重複）: {row.get('title', '不明')}")
                        continue

                    parsed_date = parse_date_flexibly(row['date'])

                    video = Video(
                        title=row['title'],
                        channel=row['channel'],
                        date=parsed_date,
                        url=row['url'],
                        playlist=row['playlist'].strip() if row['playlist'].strip() else 'Not listed in a playlist'
                    )

                    videos.append(video)
                    existing_urls.add(url)  # CSV内での重複も防止

                except Exception as e:
                    self.stderr.write(f"スキップ（エラー）: {row.get('title', '不明')} 理由: {e}")

        Video.objects.bulk_create(videos)
        self.stdout.write(self.style.SUCCESS(f"{len(videos)} 件の動画をインポートしました。"))
