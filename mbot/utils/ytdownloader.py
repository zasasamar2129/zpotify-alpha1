# /workspace/zpotify-alpha/mbot/utils/ytdownloader.py
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
import os
import json
import aiohttp
from yt_dlp import YoutubeDL
from requests import get
from asgiref.sync import sync_to_async
import traceback
from functools import wraps
import logging
from urllib.parse import quote
import re
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load cookies if available
COOKIES_FILE = os.getenv('YT_COOKIES_FILE', '/tmp/yt_cookies.txt')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
RAPIDAPI_HOST = "youtube-mp36.p.rapidapi.com"  # Example API, you can change this

# Add this helper function
def sanitize_filename(filename):
    """Sanitize filename by removing special characters"""
    # Remove special characters but keep spaces
    filename = re.sub(r'[^\w\s-]', '', filename).strip()
    # Replace spaces with underscores
    filename = re.sub(r'[-\s]+', '_', filename)
    return filename


class DownloadError(Exception):
    pass

def retry_on_failure(max_retries=3):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise DownloadError(f"All {max_retries} attempts failed") from last_exception
        return wrapper
    return decorator

@sync_to_async
def get_video_info(url, ydl_opts=None):
    """Get video information using yt-dlp"""
    if ydl_opts is None:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"Failed to get video info: {str(e)}")
        raise DownloadError(f"Could not retrieve video info: {str(e)}")

@sync_to_async
def download_with_ytdlp(url, opts):
    """Download using yt-dlp with the given options"""
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)
            return ydl.prepare_filename(info)
    except Exception as e:
        logger.error(f"YT-DLP download failed: {str(e)}")
        raise DownloadError(f"YT-DLP download failed: {str(e)}")

@sync_to_async
def download_with_cookies(url, opts):
    """Download using yt-dlp with cookies"""
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    else:
        logger.warning("Cookies file not found, proceeding without cookies")
    
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)
            return ydl.prepare_filename(info)
    except Exception as e:
        logger.error(f"Cookies download failed: {str(e)}")
        raise DownloadError(f"Cookies download failed: {str(e)}")

async def download_with_rapidapi(url, opts):
    """Download using RapidAPI as a fallback"""
    if not RAPIDAPI_KEY:
        raise DownloadError("No RapidAPI key configured")
    
    try:
        # First extract video ID from URL
        video_id = extract_video_id(url)
        if not video_id:
            raise DownloadError("Could not extract video ID from URL")
        
        # Use RapidAPI to get download link
        download_url = await get_rapidapi_download_link(video_id)
        
        # Download the file using the obtained URL
        return await download_from_url(download_url, opts['outtmpl'])
    except Exception as e:
        logger.error(f"RapidAPI download failed: {str(e)}")
        raise DownloadError(f"RapidAPI download failed: {str(e)}")

async def get_rapidapi_download_link(video_id):
    """Get download link from RapidAPI"""
    url = f"https://{RAPIDAPI_HOST}/dl"
    params = {"id": video_id}
    
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('status') == 'ok' and data.get('link'):
                    return data['link']
                raise DownloadError(f"API returned error: {data.get('msg', 'Unknown error')}")
            raise DownloadError(f"API request failed with status {response.status}")

async def download_from_url(download_url, outtmpl):
    """Download file from direct URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url) as response:
            if response.status == 200:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(outtmpl), exist_ok=True)
                
                # Save the file
                with open(outtmpl, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                return outtmpl
            raise DownloadError(f"Download failed with status {response.status}")

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    # This is a simplified version - you might want to use a more robust method
    if 'youtube.com/watch?v=' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    return None

@retry_on_failure(max_retries=3)
async def robust_download(url, download_opts):
    """Try multiple download methods with fallback"""
    methods = [
        download_with_ytdlp,
        download_with_cookies,
        download_with_rapidapi
    ]
    
    # Sanitize the output template filename
    if 'outtmpl' in download_opts:
        base_dir = os.path.dirname(download_opts['outtmpl'])
        filename = os.path.basename(download_opts['outtmpl'])
        sanitized = sanitize_filename(filename)
        download_opts['outtmpl'] = os.path.join(base_dir, sanitized)
    
    last_error = None
    for method in methods:
        try:
            result = await method(url, download_opts.copy())
            logger.info(f"Successfully downloaded using {method.__name__}")
            
            # Ensure the file exists and is accessible
            if not os.path.exists(result):
                # Try to find the actual file with sanitized name
                dir_path = os.path.dirname(result)
                actual_files = [f for f in os.listdir(dir_path) if f.startswith(os.path.splitext(sanitize_filename(os.path.basename(result)))[0])]
                if actual_files:
                    result = os.path.join(dir_path, actual_files[0])
            
            return result
        except DownloadError as e:
            last_error = e
            logger.warning(f"Method {method.__name__} failed, trying next method...")
            continue
    
    if last_error:
        raise last_error
    raise DownloadError("All download methods failed")


@sync_to_async
def thumb_down(videoId):
    """Download thumbnail with retry logic"""
    try:
        thumbnail_url = f"https://img.youtube.com/vi/{videoId}/maxresdefault.jpg"
        response = get(thumbnail_url, timeout=10)
        if response.status_code == 200:
            path = f"/tmp/thumbnails/{videoId}.jpg"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as file:
                file.write(response.content)
            return path
        
        # Fallback to default thumbnail if maxres not available
        thumbnail_url = f"https://img.youtube.com/vi/{videoId}/default.jpg"
        response = get(thumbnail_url, timeout=10)
        if response.status_code == 200:
            path = f"/tmp/thumbnails/{videoId}.jpg"
            with open(path, "wb") as file:
                file.write(response.content)
            return path
        raise DownloadError("Could not download thumbnail")
    except Exception as e:
        logger.error(f"Thumbnail download failed: {str(e)}")
        raise DownloadError(f"Thumbnail download failed: {str(e)}")