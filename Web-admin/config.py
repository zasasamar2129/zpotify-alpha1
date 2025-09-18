import os 
# Flask configuration
DEBUG = True
SECRET_KEY = 'ALPHA'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))             
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))  

# Web admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'  # Change this in production
TELEGRAM_TOKEN = '7688318906:AAF2wCe6hE4Dp5yIDh0WU6rQxYvSDtI0tHQ' # Add your bot token to config.py

# Bot paths 
DB_FOLDER = "database"
BOT_PATH = '/workspace/zpotify-alpha'  # Update this with your bot's path
LOG_FILE = os.path.join(BOT_PATH, 'bot.log')
USER_INFO_PATH = os.path.join(PROJECT_ROOT, 'database', 'user_info.json')
BAN_LIST_FILE = os.path.join(PROJECT_ROOT, 'database', "banned_users.json")
MAINTENANCE_FILE = os.path.join(PROJECT_ROOT, 'database', 'maintenance_status.json')
CONFIG_ENV_PATH = os.path.join(PROJECT_ROOT, 'config.env')

