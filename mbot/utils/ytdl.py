# /workspace/zpotify-alpha/mbot/utils/ytdl.py
"""MIT License

Copyright (c) 2025 ZACO

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from asgiref.sync import sync_to_async
from yt_dlp import YoutubeDL
from requests import get
from .ytdownloader import robust_download, thumb_down as robust_thumb_down

@sync_to_async
def getIds(video):
    ids = []
    with YoutubeDL({'quiet':True}) as ydl:
        info_dict = ydl.extract_info(video, download=False)
        try:
            info_dict = info_dict['entries']
            ids.extend([x.get('id'),x.get('playlist_index'),x.get('creator') or x.get('uploader'),x.get('title'),x.get('duration'),x.get('thumbnail')] for x in info_dict)
        except:
            ids.append([info_dict.get('id'),info_dict.get('playlist_index'),info_dict.get('creator') or info_dict.get('uploader'),info_dict.get('title'),info_dict.get('duration'),info_dict.get('thumbnail')])
    return ids

def audio_opt(path, uploader="@YouNeedMusicBot"):
    return {
        "format": "bestaudio",
        "addmetadata": True,
        "geo_bypass": True,
        'noplaylist': True,
        "nocheckcertificate": True,
        "outtmpl": f"{path}/%(title)s - {uploader}.mp3",
        "quiet": True,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_args": {
            "youtube": {
                "skip": ["hls", "dash"]
            }
        },
        # Additional metadata options
        "postprocessor_args": [
            "-metadata", f"title=%(title)s",
            "-metadata", f"artist=%(uploader)s",
            "-metadata", "comment=Downloaded via @z_downloadbot"
        ]
    }

@sync_to_async
def ytdl_down(opts, url):
    """This now uses the robust downloader"""
    return robust_download(url, opts)

@sync_to_async
def thumb_down(videoId):
    """Use the robust thumbnail downloader"""
    return robust_thumb_down(videoId)