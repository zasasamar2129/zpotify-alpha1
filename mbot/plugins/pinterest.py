import os
import asyncio
import aiohttp
import aiofiles
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse, unquote
from pyrogram import filters, Client
from pyrogram.types import Message
from mbot import Mbot, LOG_GROUP, AUTH_CHATS
from mbot.utils.util import is_maintenance_mode
from mbot.utils.language_utils import get_user_language
from mbot.utils.premium import (
    premium_required,
    cooldown_required,
    daily_limit_required,
    premium
)

from mbot.__init__ import (
    BAN_LIST_FILE, 
    MAINTENANCE_FILE, 
    USER_LIST_FILE, 
    USER_INFO_FILE, 
    USER_LANGUAGES_FILE, 
    PREMIUM_USERS_FILE, 
    PREMIUM_COOLDOWN_FILE, 
    DAILY_LIMITS_FILE)
# Configure logging

# Load banned users from file
def load_banned_users():
    if os.path.exists(BAN_LIST_FILE):
        with open(BAN_LIST_FILE, "r") as f:
            return set(json.load(f))
    return set()
banned_users = load_banned_users()

logger = logging.getLogger(__name__)


# Add these dictionaries to your pinterest.py file, preferably near the other response dictionaries

PINTEREST_RESPONSES = {
    "en": {
        "processing": "🔄 Processing Pinterest link...",
        "processing_board": "🔄 Processing Pinterest board...",
        "download_success": "✅ Successfully downloaded Pinterest content",
        "pin_success": "📌 Pinterest pin downloaded successfully",
        "board_success": "📌 Successfully downloaded {count} pins from board",
        "error": "❌ Error downloading from Pinterest: {error}",
        "invalid_url": "⚠️ Invalid Pinterest URL format",
        "no_content": "⚠️ No downloadable content found",
        "rate_limit": "⚠️ Please wait before downloading more content",
        "maintenance": "🔧 Pinterest downloader is under maintenance",
        "banned": "🚫 You are banned from using this feature",
        "premium_required": "💎 Premium feature - upgrade to access",
        "cooldown": "⏳ Please wait {time} before downloading again",
        "daily_limit": "📊 You've reached your daily download limit",
        "media_caption": "📌 {title}\n\n{description}",
        "video_caption": "📹 {title}\n\n{description}",
        "board_limit": "Showing first {limit} pins from board"
    },
    "fa": {
        "processing": "🔄 در حال پردازش لینک Pinterest...",
        "processing_board": "🔄 در حال پردازش تخته Pinterest...",
        "download_success": "✅ محتوای Pinterest با موفقیت دانلود شد",
        "pin_success": "📌 پین Pinterest با موفقیت دانلود شد",
        "board_success": "📌 {count} پین از تخته با موفقیت دانلود شد",
        "error": "❌ خطا در دانلود از Pinterest: {error}",
        "invalid_url": "⚠️ فرمت URL نادرست است",
        "no_content": "⚠️ محتوایی برای دانلود یافت نشد",
        "rate_limit": "⚠️ لطفاً قبل از دانلود بیشتر صبر کنید",
        "maintenance": "🔧 دانلودر Pinterest در حال تعمیر است",
        "banned": "🚫 شما از استفاده از این ویژگی محروم هستید",
        "premium_required": "💎 ویژگی پریمیوم - برای دسترسی ارتقا دهید",
        "cooldown": "⏳ لطفاً {time} قبل از دانلود مجدد صبر کنید",
        "daily_limit": "📊 به حد مجاز دانلود روزانه رسیده‌اید",
        "media_caption": "📌 {title}\n\n{description}",
        "video_caption": "📹 {title}\n\n{description}",
        "board_limit": "نمایش اولین {limit} پین از تخته"
    },
    "es": {
        "processing": "🔄 Procesando enlace de Pinterest...",
        "processing_board": "🔄 Procesando tablero de Pinterest...",
        "download_success": "✅ Contenido de Pinterest descargado con éxito",
        "pin_success": "📌 Pin de Pinterest descargado con éxito",
        "board_success": "📌 {count} pines del tablero descargados con éxito",
        "error": "❌ Error al descargar de Pinterest: {error}",
        "invalid_url": "⚠️ Formato de URL no válido",
        "no_content": "⚠️ No se encontró contenido para descargar",
        "rate_limit": "⚠️ Por favor espere antes de descargar más contenido",
        "maintenance": "🔧 El descargador de Pinterest está en mantenimiento",
        "banned": "🚫 Tienes prohibido usar esta función",
        "premium_required": "💎 Función premium - actualiza para acceder",
        "cooldown": "⏳ Por favor espera {time} antes de descargar de nuevo",
        "daily_limit": "📊 Has alcanzado tu límite diario de descargas",
        "media_caption": "📌 {title}\n\n{description}",
        "video_caption": "📹 {title}\n\n{description}",
        "board_limit": "Mostrando los primeros {limit} pines del tablero"
    },
    "ru": {
        "processing": "🔄 Обработка ссылки Pinterest...",
        "processing_board": "🔄 Обработка доски Pinterest...",
        "download_success": "✅ Контент Pinterest успешно загружен",
        "pin_success": "📌 Пин Pinterest успешно загружен",
        "board_success": "📌 {count} пинов с доски успешно загружены",
        "error": "❌ Ошибка загрузки из Pinterest: {error}",
        "invalid_url": "⚠️ Неверный формат URL",
        "no_content": "⚠️ Не найдено контента для загрузки",
        "rate_limit": "⚠️ Пожалуйста, подождите перед загрузкой нового контента",
        "maintenance": "🔧 Загрузчик Pinterest на техническом обслуживании",
        "banned": "🚫 Вам запрещено использовать эту функцию",
        "premium_required": "💎 Премиум функция - обновитесь для доступа",
        "cooldown": "⏳ Пожалуйста, подождите {time} перед повторной загрузкой",
        "daily_limit": "📊 Вы достигли дневного лимита загрузок",
        "media_caption": "📌 {title}\n\n{description}",
        "video_caption": "📹 {title}\n\n{description}",
        "board_limit": "Показаны первые {limit} пинов с доски"
    },
    "ar": {
        "processing": "🔄 جاري معالجة رابط Pinterest...",
        "processing_board": "🔄 جاري معالجة لوحة Pinterest...",
        "download_success": "✅ تم تنزيل محتوى Pinterest بنجاح",
        "pin_success": "📌 تم تنزيل دبوس Pinterest بنجاح",
        "board_success": "📌 تم تنزيل {count} دبوس من اللوحة بنجاح",
        "error": "❌ خطأ في التنزيل من Pinterest: {error}",
        "invalid_url": "⚠️ تنسيق URL غير صالح",
        "no_content": "⚠️ لم يتم العثور على محتوى للتنزيل",
        "rate_limit": "⚠️ يرجى الانتظار قبل تنزيل المزيد من المحتوى",
        "maintenance": "🔧 أداة تنزيل Pinterest قيد الصيانة",
        "banned": "🚫 ممنوع من استخدام هذه الميزة",
        "premium_required": "💎 ميزة مميزة - قم بالترقية للوصول",
        "cooldown": "⏳ يرجى الانتظار {time} قبل التنزيل مرة أخرى",
        "daily_limit": "📊 لقد وصلت إلى حد التنزيل اليومي",
        "media_caption": "📌 {title}\n\n{description}",
        "video_caption": "📹 {title}\n\n{description}",
        "board_limit": "عرض أول {limit} دبوس من اللوحة"
    },
    "hi": {
        "processing": "🔄 Pinterest लिंक प्रोसेस कर रहा हूँ...",
        "processing_board": "🔄 Pinterest बोर्ड प्रोसेस कर रहा हूँ...",
        "download_success": "✅ Pinterest सामग्री सफलतापूर्वक डाउनलोड की गई",
        "pin_success": "📌 Pinterest पिन सफलतापूर्वक डाउनलोड की गई",
        "board_success": "📌 बोर्ड से {count} पिन सफलतापूर्वक डाउनलोड की गईं",
        "error": "❌ Pinterest से डाउनलोड करने में त्रुटि: {error}",
        "invalid_url": "⚠️ अमान्य URL प्रारूप",
        "no_content": "⚠️ डाउनलोड के लिए कोई सामग्री नहीं मिली",
        "rate_limit": "⚠️ कृपया अधिक सामग्री डाउनलोड करने से पहले प्रतीक्षा करें",
        "maintenance": "🔧 Pinterest डाउनलोडर रखरखाव में है",
        "banned": "🚫 आपको इस सुविधा का उपयोग करने से प्रतिबंधित किया गया है",
        "premium_required": "💎 प्रीमियम सुविधा - पहुंच के लिए अपग्रेड करें",
        "cooldown": "⏳ कृपया फिर से डाउनलोड करने से पहले {time} प्रतीक्षा करें",
        "daily_limit": "📊 आप अपनी दैनिक डाउनलोड सीमा तक पहुँच चुके हैं",
        "media_caption": "📌 {title}\n\n{description}",
        "video_caption": "📹 {title}\n\n{description}",
        "board_limit": "बोर्ड से पहले {limit} पिन दिखा रहा हूँ"
    }
}

PINTEREST_STRINGS = {
    "en": {
        "pin": "📌 Pin",
        "board": "📋 Board",
        "image": "🖼️ Image",
        "video": "🎥 Video",
        "from": "From",
        "pinterest": "Pinterest",
        "download": "Download",
        "content": "Content",
        "username": "Username",
        "description": "Description",
        "date": "Date",
        "size": "Size",
        "dimensions": "Dimensions",
        "duration": "Duration",
        "views": "Views",
        "likes": "Likes",
        "comments": "Comments",
        "saves": "Saves",
        "creator": "Creator",
        "link": "Link",
        "quality": "Quality",
        "type": "Type",
        "status": "Status",
        "success": "Success",
        "failed": "Failed",
        "processing": "Processing",
        "available": "Available",
        "unavailable": "Unavailable",
        "premium": "Premium",
        "free": "Free",
        "limit": "Limit",
        "remaining": "Remaining",
        "total": "Total"
    },
    "fa": {
        "pin": "📌 پین",
        "board": "📋 تخته",
        "image": "🖼️ تصویر",
        "video": "🎥 ویدیو",
        "from": "از",
        "pinterest": "Pinterest",
        "download": "دانلود",
        "content": "محتوا",
        "username": "نام کاربری",
        "description": "توضیحات",
        "date": "تاریخ",
        "size": "اندازه",
        "dimensions": "ابعاد",
        "duration": "مدت زمان",
        "views": "بازدیدها",
        "likes": "لایک‌ها",
        "comments": "نظرات",
        "saves": "ذخیره‌ها",
        "creator": "سازنده",
        "link": "لینک",
        "quality": "کیفیت",
        "type": "نوع",
        "status": "وضعیت",
        "success": "موفق",
        "failed": "ناموفق",
        "processing": "در حال پردازش",
        "available": "موجود",
        "unavailable": "ناموجود",
        "premium": "پریمیوم",
        "free": "رایگان",
        "limit": "محدودیت",
        "remaining": "باقی‌مانده",
        "total": "مجموع"
    },
    "es": {
        "pin": "📌 Pin",
        "board": "📋 Tablero",
        "image": "🖼️ Imagen",
        "video": "🎥 Video",
        "from": "De",
        "pinterest": "Pinterest",
        "download": "Descargar",
        "content": "Contenido",
        "username": "Nombre de usuario",
        "description": "Descripción",
        "date": "Fecha",
        "size": "Tamaño",
        "dimensions": "Dimensiones",
        "duration": "Duración",
        "views": "Vistas",
        "likes": "Me gusta",
        "comments": "Comentarios",
        "saves": "Guardados",
        "creator": "Creador",
        "link": "Enlace",
        "quality": "Calidad",
        "type": "Tipo",
        "status": "Estado",
        "success": "Éxito",
        "failed": "Fallido",
        "processing": "Procesando",
        "available": "Disponible",
        "unavailable": "No disponible",
        "premium": "Premium",
        "free": "Gratis",
        "limit": "Límite",
        "remaining": "Restante",
        "total": "Total"
    },
    "ru": {
        "pin": "📌 Пин",
        "board": "📋 Доска",
        "image": "🖼️ Изображение",
        "video": "🎥 Видео",
        "from": "Из",
        "pinterest": "Pinterest",
        "download": "Скачать",
        "content": "Контент",
        "username": "Имя пользователя",
        "description": "Описание",
        "date": "Дата",
        "size": "Размер",
        "dimensions": "Размеры",
        "duration": "Продолжительность",
        "views": "Просмотры",
        "likes": "Лайки",
        "comments": "Комментарии",
        "saves": "Сохранения",
        "creator": "Создатель",
        "link": "Ссылка",
        "quality": "Качество",
        "type": "Тип",
        "status": "Статус",
        "success": "Успех",
        "failed": "Неудача",
        "processing": "Обработка",
        "available": "Доступно",
        "unavailable": "Недоступно",
        "premium": "Премиум",
        "free": "Бесплатно",
        "limit": "Лимит",
        "remaining": "Осталось",
        "total": "Всего"
    },
    "ar": {
        "pin": "📌 دبوس",
        "board": "📋 لوحة",
        "image": "🖼️ صورة",
        "video": "🎥 فيديو",
        "from": "من",
        "pinterest": "Pinterest",
        "download": "تنزيل",
        "content": "محتوى",
        "username": "اسم المستخدم",
        "description": "وصف",
        "date": "تاريخ",
        "size": "حجم",
        "dimensions": "أبعاد",
        "duration": "مدة",
        "views": "مشاهدات",
        "likes": "إعجابات",
        "comments": "تعليقات",
        "saves": "حفظ",
        "creator": "المنشئ",
        "link": "رابط",
        "quality": "جودة",
        "type": "نوع",
        "status": "حالة",
        "success": "نجاح",
        "failed": "فشل",
        "processing": "جاري المعالجة",
        "available": "متاح",
        "unavailable": "غير متاح",
        "premium": "بريميوم",
        "free": "مجاني",
        "limit": "حد",
        "remaining": "متبقي",
        "total": "المجموع"
    },
    "hi": {
        "pin": "📌 पिन",
        "board": "📋 बोर्ड",
        "image": "🖼️ छवि",
        "video": "🎥 वीडियो",
        "from": "से",
        "pinterest": "Pinterest",
        "download": "डाउनलोड",
        "content": "सामग्री",
        "username": "उपयोगकर्ता नाम",
        "description": "विवरण",
        "date": "तिथि",
        "size": "आकार",
        "dimensions": "आयाम",
        "duration": "अवधि",
        "views": "दृश्य",
        "likes": "पसंद",
        "comments": "टिप्पणियाँ",
        "saves": "सहेजे गए",
        "creator": "निर्माता",
        "link": "लिंक",
        "quality": "गुणवत्ता",
        "type": "प्रकार",
        "status": "स्थिति",
        "success": "सफल",
        "failed": "असफल",
        "processing": "प्रसंस्करण",
        "available": "उपलब्ध",
        "unavailable": "अनुपलब्ध",
        "premium": "प्रीमियम",
        "free": "मुफ्त",
        "limit": "सीमा",
        "remaining": "शेष",
        "total": "कुल"
    }
}

class PinterestDownloader:
    def __init__(self, download_path: str = "downloads/pinterest"):
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def _extract_images_from_json(self, pin_data: Dict) -> List[Dict]:
        """Extract unique image URLs from Pinterest JSON data"""
        images = []
        seen_urls = set()
        
        def add_unique_image(url: str, width: int = None, height: int = None):
            if url and url not in seen_urls:
                seen_urls.add(url)
                images.append({
                    'url': url,
                    'width': width,
                    'height': height
                })

        if 'images' in pin_data:
            size_preference = ['orig', 'x1200', 'x1000', 'x800', 'x600']
            for size in size_preference:
                if size in pin_data['images']:
                    data = pin_data['images'][size]
                    if isinstance(data, dict) and 'url' in data:
                        add_unique_image(
                            data['url'],
                            data.get('width'),
                            data.get('height')
                        )

        story_pin = pin_data.get('story_pin_data', {})
        if story_pin and 'pages' in story_pin:
            for page in story_pin['pages']:
                for block in page.get('blocks', []):
                    if 'image' in block:
                        image_data = block['image']
                        if isinstance(image_data, dict) and 'images' in image_data:
                            images_list = list(image_data['images'].values())
                            images_list.sort(
                                key=lambda x: (x.get('width', 0) * x.get('height', 0)),
                                reverse=True
                            )
                            for img in images_list:
                                if 'url' in img:
                                    add_unique_image(
                                        img['url'],
                                        img.get('width'),
                                        img.get('height')
                                    )
        
        logger.info(f"Extracted {len(images)} images from JSON")
        return images

    def _extract_images_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract unique and high-quality images from Pinterest HTML"""
        images = []
        seen_urls = set()

        def normalize_url(url: str) -> str:
            return url.split('?')[0]

        def add_unique_image(url: str, width: int = None, height: int = None):
            if not url:
                return
            normalized_url = normalize_url(url)
            if normalized_url in seen_urls:
                return
            if any(x in url.lower() for x in ['/237x/', '/75x/']):
                return
            seen_urls.add(normalized_url)
            images.append({
                'url': normalized_url,
                'width': width,
                'height': height
            })

        carousel_divs = soup.find_all('div', {'data-test-id': re.compile(r'carousel-img-\d+')})
        for carousel in carousel_divs:
            img_tag = carousel.find('img')
            if img_tag:
                src = img_tag.get('src', '')
                srcset = img_tag.get('srcset', '').split(',')
                best_url = src
                for srcset_item in srcset:
                    parts = srcset_item.strip().split()
                    if len(parts) >= 1 and '736x' in parts[0]:
                        best_url = parts[0]
                        break
                if '736x' not in best_url:
                    best_url = re.sub(r'/\d+x/', '/736x/', best_url)
                add_unique_image(best_url)

        quality_indicators = ['/originals/', '/736x/', '/564x/', '/550x/', '/474x/']
        for img in soup.find_all('img', {'src': True}):
            src = img.get('src', '')
            if any(x in src.lower() for x in quality_indicators):
                add_unique_image(src)

        images.sort(
            key=lambda x: (x.get('width', 0) or 0) * (x.get('height', 0) or 0),
            reverse=True
        )
        return images
    
    async def _resolve_short_url(self, url: str) -> str:
        """Resolve pin.it short URL to full Pinterest URL"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        return str(response.url)
            return url
        except Exception as e:
            logger.error(f"Error resolving short URL: {str(e)}")
            return url

    def _normalize_pinterest_url(self, url: str) -> str:
        """Convert any Pinterest URL to standard format"""
        url = url.split('?')[0].rstrip('/')
        parsed = urlparse(url)
        
        if any(domain in parsed.netloc for domain in ['pin.it', 'pinterest.com', 'www.pinterest.com']) or \
           parsed.netloc.endswith('pinterest.com'):
            path = parsed.path.strip('/')
            if 'pin' in path:
                pin_id = re.search(r'pin[/]?([0-9]+)', path)
                if pin_id:
                    return f"https://www.pinterest.com/pin/{pin_id.group(1)}"
            return f"https://www.pinterest.com/{path}"
        return url

    async def _parse_url(self, url: str) -> Dict:
        """Parse Pinterest URL to determine content type"""
        if "pin.it" in url:
            url = await self._resolve_short_url(url)
        
        url = self._normalize_pinterest_url(url)
        
        if "/pin/" in url:
            pin_id = url.split("/pin/")[1].split("/")[0]
            return {"type": "pin", "id": pin_id}
        elif "/board/" in url:
            parts = url.split("/board/")[1].split("/")
            return {"type": "board", "username": parts[0], "board_name": parts[1]}
        else:
            raise ValueError("Unsupported Pinterest URL")

    async def _get_pin_data(self, pin_id: str) -> Dict:
        """Extract pin data and all associated images"""
        urls_to_try = [
            f"https://www.pinterest.com/pin/{pin_id}/",
            f"https://pinterest.com/pin/{pin_id}/"
        ]
        
        for url in urls_to_try:
            try:
                async with aiohttp.ClientSession(headers=self.headers) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            continue
                        
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        pin_data = {
                            'title': '',
                            'description': '',
                            'images': []
                        }

                        meta_title = soup.find('meta', property='og:title')
                        meta_desc = soup.find('meta', property='og:description')
                        pin_data['title'] = meta_title.get('content', '') if meta_title else ''
                        pin_data['description'] = meta_desc.get('content', '') if meta_desc else ''

                        for script in soup.find_all('script', type='application/json'):
                            try:
                                data = json.loads(script.string)
                                if 'props' in data and 'initialReduxState' in data['props']:
                                    pins = data['props']['initialReduxState'].get('pins', {})
                                    if pin_id in pins:
                                        json_images = self._extract_images_from_json(pins[pin_id])
                                        if json_images:
                                            pin_data['images'].extend(json_images)
                            except json.JSONDecodeError:
                                continue

                        if not pin_data['images']:
                            html_images = self._extract_images_from_html(soup)
                            pin_data['images'].extend(html_images)

                        if pin_data['images']:
                            return pin_data

            except Exception as e:
                logger.error(f"Error fetching from {url}: {str(e)}")
                continue

        raise Exception("Pin data not found")

    async def _download_file(self, url: str, filename: str) -> bool:
        """Download a file asynchronously"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        filepath = self.download_path / filename
                        async with aiofiles.open(filepath, 'wb') as f:
                            await f.write(await response.read())
                        return True
            return False
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False

    async def download_pin(self, url: str) -> Dict:
        """Download all images from a Pinterest pin"""
        try:
            parsed = await self._parse_url(url)
            if parsed["type"] != "pin":
                raise ValueError("URL must be a Pinterest pin")

            pin_data = await self._get_pin_data(parsed["id"])
            
            if not pin_data['images']:
                raise Exception("No images found in pin")

            unique_images = []
            seen_urls = set()
            for image in pin_data['images']:
                url = image['url']
                base_url = re.sub(r'/\d+x/', '/736x/', url)
                if base_url not in seen_urls:
                    seen_urls.add(base_url)
                    image['url'] = base_url
                    unique_images.append(image)

            downloaded_files = []
            for idx, image in enumerate(unique_images):
                try:
                    image_url = image['url']
                    suffix = Path(urlparse(image_url).path).suffix or '.jpg'
                    filename = f"pin_{parsed['id']}_{idx+1}{suffix}"
                    
                    success = await self._download_file(image_url, filename)
                    if success:
                        downloaded_files.append(str(self.download_path / filename))
                except Exception as e:
                    logger.error(f"Error downloading image {idx+1}: {str(e)}")

            if not downloaded_files:
                raise Exception("Failed to download any images")

            return {
                'success': True,
                'id': parsed["id"],
                'title': pin_data.get('title', ''),
                'description': pin_data.get('description', ''),
                'paths': downloaded_files,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error downloading pin: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    async def download_board(self, url: str, limit: Optional[int] = None) -> List[Dict]:
        """Download all pins from a Pinterest board"""
        try:
            parsed = await self._parse_url(url)
            if parsed["type"] != "board":
                raise ValueError("URL must be a Pinterest board")

            pin_ids = await self._get_board_pins(parsed["username"], parsed["board_name"])

            if limit:
                pin_ids = pin_ids[:limit]

            results = []
            for pin_id in pin_ids:
                pin_url = f"https://www.pinterest.com/pin/{pin_id}/"
                result = await self.download_pin(pin_url)
                results.append(result)
                await asyncio.sleep(1)  # Rate limiting

            return results

        except Exception as e:
            logger.error(f"Error downloading board: {str(e)}")
            return [{
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }]

    async def _get_board_pins(self, username: str, board_name: str) -> List[str]:
        """Get all pin IDs from a board"""
        board_url = f"https://www.pinterest.com/{username}/{board_name}/"
        pin_ids = []

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(board_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch board data. Status: {response.status}")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    for script in soup.find_all('script', type='application/json'):
                        try:
                            data = json.loads(script.string)
                            if 'props' in data and 'initialReduxState' in data['props']:
                                board_data = data['props']['initialReduxState']
                                if 'pins' in board_data:
                                    pin_ids.extend(board_data['pins'].keys())
                        except json.JSONDecodeError:
                            continue
                    
                    if not pin_ids:
                        for element in soup.find_all(['div', 'a']):
                            pin_id = None
                            data_id = element.get('data-test-id', '')
                            href = element.get('href', '')
                            
                            if 'pin' in data_id:
                                pin_id = data_id.replace('pin', '')
                            elif '/pin/' in href:
                                pin_id = href.split('/pin/')[1].split('/')[0]
                            
                            if pin_id and pin_id.isdigit():
                                pin_ids.append(pin_id)

            return list(set(pin_ids))

        except Exception as e:
            logger.error(f"Error fetching board data: {str(e)}")
            raise Exception(f"Error fetching board data: {str(e)}")

pinterest_downloader = PinterestDownloader()

@Mbot.on_message(
    filters.incoming & 
    (
        filters.regex(r'https?://(?:www\.)?pinterest\.(?:com|it)/pin/[^\s]+') |
        filters.regex(r'https?://pin\.it/[^\s]+')
    ) & 
    (filters.private | filters.chat(AUTH_CHATS)))
@premium_required()
async def handle_pinterest_links(client: Client, message: Message):
    user_lang = get_user_language(message.from_user.id)
    lang_responses = PINTEREST_RESPONSES.get(user_lang, PINTEREST_RESPONSES["en"])
    lang_strings = PINTEREST_STRINGS.get(user_lang, PINTEREST_STRINGS["en"])
    # Check maintenance mode
    if is_maintenance_mode() and message.from_user.id not in SUDO_USERS:
        await message.reply_text(PINTEREST_RESPONSES.get(user_lang, {}).get("maintenance","🔧 The bot is under maintenance. Please try again later."))
        return

    # Check Banned Users
    if message.from_user.id in banned_users:
        await message.reply_text(PINTEREST_RESPONSES.get(user_lang, {}).get("banned","You are banned from using this bot  ദ്ദി ༎ຶ‿༎ຶ ) "))
        return

    url = message.text
    msg = await message.reply_text(lang_responses["processing"])
    
    try:
        result = await pinterest_downloader.download_pin(url)
        
        if not result['success']:
            await msg.edit(f"❌ Error downloading from Pinterest: {result['error']}")
            return

        for file_path in result['paths']:
            try:
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    await message.reply_photo(
                        file_path,
                        caption=lang_responses["media_caption"].format(
                            title=result.get('title', lang_strings["pin"]),
                            description=result.get('description', '')
                        )[:1024],
                        reply_to_message_id=message.id
                    )
                elif file_path.lower().endswith(('.mp4', '.mov', '.gif')):
                    await message.reply_video(
                        file_path,
                        caption=lang_responses["video_caption"].format(
                            title=result.get('title', lang_strings["pin"]),
                            description=result.get('description', '')
                        )[:1024],
                        reply_to_message_id=message.id
                    )
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error sending Pinterest content: {str(e)}")
                if os.path.exists(file_path):
                    os.remove(file_path)

        await msg.delete()

    except Exception as e:
        await msg.edit(lang_responses["error"].format(error=str(e)))

@Mbot.on_message(
    filters.incoming & 
    filters.regex(r'https?://(?:www\.)?pinterest\.(?:com|it)/[^/]+/[^/\s]+') & 
    (filters.private | filters.chat(AUTH_CHATS)))
@premium_required()
async def handle_pinterest_boards(client: Client, message: Message):
    user_lang = get_user_language(message.from_user.id)
    lang_responses = PINTEREST_RESPONSES.get(user_lang, PINTEREST_RESPONSES["en"])
    lang_strings = PINTEREST_STRINGS.get(user_lang, PINTEREST_STRINGS["en"])

    # Check maintenance mode
    if is_maintenance_mode() and message.from_user.id not in SUDO_USERS:
        await message.reply_text(PINTEREST_RESPONSES.get(user_lang, {}).get("maintenance","🔧 The bot is under maintenance. Please try again later."))
        return

    # Check Banned Users
    if message.from_user.id in banned_users:
        await message.reply_text(PINTEREST_RESPONSES.get(user_lang, {}).get("banned","You are banned from using this bot  ദ്ദി ༎ຶ‿༎ຶ ) "))
        return

    url = message.text
    msg = await message.reply_text(lang_responses["processing_board"])
    
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if len(path_parts) < 2:
            await msg.edit(lang_responses["invalid_url"])
            return
            
        results = await pinterest_downloader.download_board(url, limit=5)
        
        success_count = sum(1 for r in results if r['success'])
        if success_count == 0:
            await msg.edit(lang_responses["error"].format(error=error))
            return

        await msg.edit(lang_responses["board_success"].format(count=success_count))

    except Exception as e:
        await msg.edit(lang_responses["error"].format(error=str(e)))