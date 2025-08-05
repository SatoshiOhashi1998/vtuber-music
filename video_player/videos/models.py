from django.db import models
from urllib.parse import urlparse, parse_qs


class Video(models.Model):
    title = models.CharField(max_length=255)
    channel = models.CharField(max_length=255)
    date = models.DateTimeField()
    url = models.URLField()
    playlist = models.CharField(max_length=255, blank=True, null=True)

    @property
    def youtube_id(self):
        try:
            parsed = urlparse(self.url)
            if parsed.hostname == "youtu.be":
                return parsed.path[1:]
            elif "youtube" in parsed.hostname:
                return parse_qs(parsed.query).get("v", [""])[0]
        except:
            return ""

