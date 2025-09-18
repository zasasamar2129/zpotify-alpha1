import os
import json
import time
from datetime import datetime, timedelta
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from mbot import Mbot, LOG_GROUP, OWNER_ID, SUDO_USERS
os.makedirs("database", exist_ok=True)
DB_FOLDER = 'database'

# Configuration
PREMIUM_PRICE = "5 USD/month"
PREMIUM_USERS_FILE = os.path.join(DB_FOLDER,"premium_users.json")
PREMIUM_COOLDOWN_FILE = os.path.join(DB_FOLDER,"premium_cooldown.json")
DAILY_LIMITS_FILE = os.path.join(DB_FOLDER,"daily_limits.json")  # New file for tracking daily limits
DEFAULT_COOLDOWN = 60  # Default 60 seconds (can be changed to 30)
NON_PREMIUM_DAILY_LIMIT = 10  # New: Daily download limit for non-premium users

# Premium features description
PREMIUM_FEATURES = """
✨ Premium Benefits:
- Unlimited Spotify downloads
- Unlimited YouTube downloads
- Download from Instagram, Pinterest, Facebook
- No cooldown restrictions
- Highest quality audio
- No daily download limits
- Priority support
"""

class PremiumSystem:
    def __init__(self):
        self.premium_users = self._load_premium_users()
        self.cooldowns = self._load_cooldowns()
        self.daily_limits = self._load_daily_limits()  # Add this line

    def _load_premium_users(self):
        """Load premium users from file"""
        if os.path.exists(PREMIUM_USERS_FILE):
            with open(PREMIUM_USERS_FILE, "r") as f:
                return json.load(f)
        return {}

    def _load_cooldowns(self):
        """Load cooldown data from file"""
        if os.path.exists(PREMIUM_COOLDOWN_FILE):
            with open(PREMIUM_COOLDOWN_FILE, "r") as f:
                return json.load(f)
        return {}

    def _save_premium_users(self):
        """Save premium users to file"""
        with open(PREMIUM_USERS_FILE, "w") as f:
            json.dump(self.premium_users, f, indent=4)

    def _save_cooldowns(self):
        """Save cooldown data to file"""
        with open(PREMIUM_COOLDOWN_FILE, "w") as f:
            json.dump(self.cooldowns, f, indent=4)
    
    def _save_daily_limits(self):
        """Save daily limits data to file"""
        with open(DAILY_LIMITS_FILE, "w") as f:
            json.dump(self.daily_limits, f, indent=4)

    def is_premium(self, user_id: int) -> bool:
        """Check if user has active premium"""
        if user_id in SUDO_USERS or user_id == OWNER_ID:
            return True
        user_data = self.premium_users.get(str(user_id))
        if user_data:
            return user_data.get("expiry", 0) > time.time()
        return False
    
    def _load_daily_limits(self):
        """Load daily limits data from file"""
        if os.path.exists(DAILY_LIMITS_FILE):
            with open(DAILY_LIMITS_FILE, "r") as f:
                return json.load(f)
        return {}

    def check_daily_limit(self, user_id: int) -> tuple:
        """Check if user has reached daily download limit
        Returns: (remaining_downloads, reset_time)"""
        if self.is_premium(user_id):
            return (float('inf'), None)  # Premium users have unlimited downloads
        
        user_id_str = str(user_id)
        today = datetime.now().date().strftime("%Y-%m-%d")
    
        if user_id_str in self.daily_limits:
            user_data = self.daily_limits[user_id_str]
            if user_data['date'] == today:
                remaining = max(0, NON_PREMIUM_DAILY_LIMIT - user_data['count'])
                # Calculate reset time (next day 00:00 UTC)
                reset_time = (datetime.now() + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                return (remaining, reset_time)
    
        # If no record or old record, return full limit
        return (NON_PREMIUM_DAILY_LIMIT, None)


    def increment_daily_count(self, user_id: int):
        """Increment the daily download count for a user"""
        if self.is_premium(user_id):
            return  # Don't track premium users
            
        user_id_str = str(user_id)
        today = datetime.now().date().strftime("%Y-%m-%d")
        
        if user_id_str in self.daily_limits:
            if self.daily_limits[user_id_str]['date'] == today:
                self.daily_limits[user_id_str]['count'] += 1
            else:
                # New day, reset count
                self.daily_limits[user_id_str] = {'date': today, 'count': 1}
        else:
            # First download today
            self.daily_limits[user_id_str] = {'date': today, 'count': 1}
            
        self._save_daily_limits()

    def add_premium(self, user_id: int, duration_days: int = 30):
        """Add premium status to user"""
        expiry = time.time() + (duration_days * 24 * 60 * 60)
        self.premium_users[str(user_id)] = {
            "expiry": expiry,
            "added": time.time(),
            "plan": "standard"
        }
        self._save_premium_users()

    def remove_premium(self, user_id: int):
        """Remove premium status"""
        if str(user_id) in self.premium_users:
            del self.premium_users[str(user_id)]
            self._save_premium_users()

    def get_premium_info(self, user_id: int) -> str:
        """Get formatted premium info"""
        if self.is_premium(user_id):
            expiry = self.premium_users.get(str(user_id), {}).get("expiry")
            if expiry:
                expiry_date = datetime.fromtimestamp(expiry).strftime("%Y-%m-%d")
                return f"🌟 Premium Status: Active (Expires: {expiry_date})"
            return "🌟 Premium Status: Active (Lifetime)"
        return "🔹 Premium Status: Not Active"


    def check_cooldown(self, user_id: int, command: str) -> float:
        """Check remaining cooldown in seconds"""
        key = f"{user_id}_{command}"
        if key in self.cooldowns:
            remaining = self.cooldowns[key] - time.time()
            return max(0, remaining) if remaining > 0 else 0
        return 0

    def set_cooldown(self, user_id: int, command: str, hours: int):
        """Set cooldown for command"""
        key = f"{user_id}_{command}"
        self.cooldowns[key] = time.time() + (hours * 3600)
        self._save_cooldowns()

# Initialize premium system
premium = PremiumSystem()

def daily_limit_required():
    """Decorator to check daily download limit"""
    def decorator(func):
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            user_id = message.from_user.id
            
            if premium.is_premium(user_id):
                return await func(client, message, *args, **kwargs)
                
            remaining, reset_time = premium.check_daily_limit(user_id)
            
            if remaining <= 0:
                reset_str = reset_time.strftime("%Y-%m-%d %H:%M:%S UTC") if reset_time else "soon"
                await message.reply_text(
                    f"⏳ You've reached your daily download limit ({NON_PREMIUM_DAILY_LIMIT} songs)\n"
                    f"Limit will reset at: {reset_str}\n\n"
                    "✨ Upgrade to premium for unlimited downloads: /premium",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Upgrade Now", callback_data="buy_premium")]
                    ])
                )
                return
                
            # Proceed with the download
            try:
                result = await func(client, message, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in wrapped function: {e}")
                raise
            
            # Only increment count if download was successful
            if result:
                premium.increment_daily_count(user_id)
                
            return result
        return wrapper
    return decorator

def premium_required():
    """Decorator to restrict access to premium users"""
    def decorator(func):
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            user_id = message.from_user.id
            
            if not premium.is_premium(user_id):
                await message.reply_text(
                    "🔒 WOW! you found a Premium Feature\n\n"
                    "💎 Upgrade now to use this feature and many more\n\n"
                    f"{PREMIUM_FEATURES}\n\n"
                    f"Your status: {premium.get_premium_info(user_id)}\n\n"
                    "💳 Upgrade with /premium",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 Get Premium", callback_data="buy_premium")]
                    ])
                )
                return
                
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator

def cooldown_required(seconds: int = DEFAULT_COOLDOWN):
    """Decorator to implement cooldown for non-premium users"""
    def decorator(func):
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            user_id = message.from_user.id
            command = func.__name__
            
            if premium.is_premium(user_id):
                return await func(client, message, *args, **kwargs)
                
            remaining = premium.check_cooldown(user_id, command)
            if remaining > 0:
                await message.reply_text(
                    f"⏳ Please wait {int(remaining)} seconds before using this again\n"
                    "✨ Upgrade to premium for no cooldowns: /premium",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Upgrade Now", callback_data="buy_premium")]
                    ])
                )
                return
                
            premium.set_cooldown(user_id, command, seconds/3600)  # Convert seconds to hours for storage
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator

# Premium commands
@Mbot.on_message(filters.command("premium"))
async def premium_command(client: Client, message: Message):
    await message.delete()
    user_id = message.from_user.id
    status = premium.get_premium_info(user_id)
    
    await message.reply_text(
        f"🎛️ Premium Subscription\n\n"
        f"{status}\n\n"
        f"{PREMIUM_FEATURES}\n\n"
        f"💳 Price: {PREMIUM_PRICE}\n"
        "💰 <b>Payment Methods:</b> PayPal (<b>soon</b>) or Crypto (USDT/BTC)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Purchase Premium", callback_data="buy_premium")],
            [InlineKeyboardButton("❓ FAQ", url="https://t.me/zpotify1")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
    )

# Update the buy_premium_callback function
@Mbot.on_callback_query(filters.regex("^buy_premium$"))
async def buy_premium_callback(client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        f"🛒 Purchase Premium - Choose Payment Method\n\n"
        f"Your User ID: `{user_id}`\n"
        "Please select your preferred payment method:",
        reply_markup=InlineKeyboardMarkup([
            #[InlineKeyboardButton("💳 PayPal", callback_data="paypal_payment")],
            [InlineKeyboardButton("₿ Crypto (USDT/BTC)", callback_data="crypto_payment")],
            [InlineKeyboardButton("🔙 Back", callback_data="premium_back")],
            #[InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
    )

# Add new handlers for payment methods
@Mbot.on_callback_query(filters.regex("^paypal_payment$"))
async def paypal_payment_handler(client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        f"💳 PayPal Payment\n\n"
        f"To pay with PayPal, please send {PREMIUM_PRICE} to:\n"
        f"PayPal Email: example@example.com\n\n"
        f"After payment, contact @itachi2129 with:\n"
        f"- Your User ID: `{user_id}`\n"
        f"- Payment screenshot/proof\n\n"
        "Your premium will be activated within 24 hours after verification.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📨 Contact Admin", url="https://t.me/itachi2129")],
            [InlineKeyboardButton("🔙 Back", callback_data="buy_premium")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
    )

@Mbot.on_callback_query(filters.regex("^crypto_payment$"))
async def crypto_payment_handler(client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        f"₿ Crypto Payment (USDT/BTC)\n\n"
        f"To pay with cryptocurrency, please send the equivalent of {PREMIUM_PRICE} to:\n\n"
        "🔹 USDT (TRC20):\n"
        "`TAbcdefghijk1234567890`\n\n"
        "🔹 BTC:\n"
        "`3Abcdefghijk1234567890`\n\n"
        f"After payment, contact @itachi2129 with:\n"
        f"- Your User ID: `{user_id}`\n"
        f"- Transaction hash\n\n"
        "Your premium will be activated within 24 hours after verification.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📨 Contact Admin", url="https://t.me/itachi2129")],
            [InlineKeyboardButton("🔙 Back", callback_data="buy_premium")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
    )

@Mbot.on_callback_query(filters.regex("^premium_back$"))
async def premium_back_callback(client, callback_query):
    await callback_query.answer()
    await premium_command(client, callback_query.message)

# Admin commands
@Mbot.on_message(filters.command("addpremium") & filters.user(SUDO_USERS + [OWNER_ID]))
async def add_premium_command(client: Client, message: Message):
    try:
        user_id = int(message.command[1])
        days = int(message.command[2]) if len(message.command) > 2 else 30
        premium.add_premium(user_id, days)
        await message.reply_text(f"✅ Added {days} days premium for user {user_id}")
    except (IndexError, ValueError):
        await message.reply_text("Usage: /addpremium <user_id> [days]")

@Mbot.on_message(filters.command("removepremium") & filters.user(SUDO_USERS + [OWNER_ID]))
async def remove_premium_command(client: Client, message: Message):
    try:
        user_id = int(message.command[1])
        premium.remove_premium(user_id)
        await message.reply_text(f"✅ Removed premium from user {user_id}")
    except (IndexError, ValueError):
        await message.reply_text("Usage: /removepremium <user_id>")

@Mbot.on_message(filters.command("premiumlist") & filters.user(SUDO_USERS + [OWNER_ID]))
async def list_premium_command(client: Client, message: Message):
    if not premium.premium_users:
        await message.reply_text("No premium users found")
        return
    
    text = "🌟 Premium Users:\n"
    for user_id, data in premium.premium_users.items():
        expiry = data.get("expiry", "Lifetime")
        if isinstance(expiry, (int, float)):
            from datetime import datetime
            expiry = datetime.fromtimestamp(expiry).strftime("%Y-%m-%d")
        text += f"- User {user_id} (Expires: {expiry})\n"
    
    await message.reply_text(text)

@Mbot.on_callback_query(filters.regex(r"premium_status"))
async def premium_status_handler(client, callback_query):
    user = callback_query.from_user
    user_lang = get_user_language(user.id)
    responses = User_Profile.get(user_lang, User_Profile["en"])
    
    status = premium.get_premium_info(user.id)
    remaining, reset_time = premium.check_daily_limit(user.id)
    
    if premium.is_premium(user.id):
        # Premium user info
        user_data = premium.premium_users.get(str(user.id), {})
        plan = user_data.get("plan", "standard").capitalize()
        expiry = user_data.get("expiry")
        
        if expiry == "lifetime":
            expiry_text = responses['premium_lifetime']
        elif expiry:
            expiry_date = datetime.fromtimestamp(expiry).strftime("%Y-%m-%d")
            expiry_text = f"{responses['premium_expiry']} {expiry_date}"
        else:
            expiry_text = responses['premium_lifetime']
            
        status_text = (
            f"🎛️ <b>Premium Subscription</b>\n\n"
            f"🌟 {responses['premium_active']}\n"
            f"📋 {responses['premium_plan']}: {plan}\n"
            f"📅 {expiry_text}\n"
            f"📊 {responses['daily_usage']}: {responses['unlimited']}"
        )
        buttons = [
            [InlineKeyboardButton("🔙 Back", callback_data="settings")]
        ]
    else:
        # Non-premium user info
        reset_str = reset_time.strftime("%Y-%m-%d %H:%M") if reset_time else "soon"
        status_text = (
            f"🎛️ <b>Premium Subscription</b>\n\n"
            f"🔹 {responses['premium_inactive']}\n"
            f"📊 {responses['daily_usage']}: {NON_PREMIUM_DAILY_LIMIT - remaining}/{NON_PREMIUM_DAILY_LIMIT}\n"
            f"🔄 Resets at: {reset_str}\n\n"
            f"{PREMIUM_FEATURES}\n\n"
            f"💳 {PREMIUM_PRICE}"
        )
        buttons = [
            [InlineKeyboardButton("🛒 Get Premium", callback_data="buy_premium")],
            [InlineKeyboardButton("🔙 Back", callback_data="settings")]
        ]
    
    await callback_query.message.edit_text(
        status_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
@Mbot.on_message(filters.command("setcooldown") & filters.user(SUDO_USERS + [OWNER_ID]))
async def set_cooldown_command(client, message):
    try:
        global DEFAULT_COOLDOWN
        DEFAULT_COOLDOWN = int(message.command[1])
        await message.reply(f"✅ Default cooldown set to {DEFAULT_COOLDOWN} seconds")
    except (IndexError, ValueError):
        await message.reply("Usage: /setcooldown <seconds>")

User_Profile = {
    "en": {
        "premium_status":   "🌟 Premium Status",
        "premium_active":   "Active",
        "premium_inactive": "Inactive",
        "premium_expiry":   "Expires on",
        "premium_lifetime": "Lifetime"
    },
    "fa": {
        "premium_status":   "🌟 وضعیت پرمیوم",
        "premium_active":   "فعال",
        "premium_inactive": "غیرفعال",
        "premium_expiry":   "انقضا در تاریخ",
        "premium_lifetime": "مادام العمر"
    },
    "hi": {
        "premium_status":   "🌟 प्रीमियम स्थिति",
        "premium_active":   "सक्रिय",
        "premium_inactive": "अक्रिय",
        "premium_expiry":   "समाप्ति की तारीख",
        "premium_lifetime": "आजीवन"
    },
    "ru": {
        "premium_status":   "🌟 Статус премиум",
        "premium_active":   "Активен",
        "premium_inactive": "Неактивен",
        "premium_expiry":   "Истекает",
        "premium_lifetime": "Пожизненно"
    },
    "es": {
        "premium_status":   "🌟 Estado Premium",
        "premium_active":   "Activo",
        "premium_inactive": "Inactivo",
        "premium_expiry":   "Expira el",
        "premium_lifetime": "De por vida"
    },
    "ar": {
        "premium_status":   "🌟 حالة بريميوم",
        "premium_active":   "نشط",
        "premium_inactive": "غير نشط",
        "premium_expiry":   "تنتهي في",
        "premium_lifetime": "مدى الحياة"
    }
}


