import json
import os
from datetime import datetime
DB_FOLDER = "database"
os.makedirs(DB_FOLDER, exist_ok=True)
USER_INFO_FILE = os.path.join(DB_FOLDER, 'user_info.json')

def load_user_info():
    """Load user info from JSON file"""
    if os.path.exists(USER_INFO_FILE):
        with open(USER_INFO_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_user_info(user_info):
    """Save user info to JSON file"""
    with open(USER_INFO_FILE, 'w') as f:
        json.dump(user_info, f, indent=4)

def update_user_info(user_id, data):
    """Update or create user info"""
    user_info = load_user_info()
    
    if str(user_id) not in user_info:
        user_info[str(user_id)] = {
            'first_name': '',
            'last_name': '',
            'username': '',
            'notes': '',
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    user_info[str(user_id)].update(data)
    user_info[str(user_id)]['updated_at'] = datetime.now().isoformat()
    save_user_info(user_info)
    return user_info[str(user_id)]

def get_user_info(user_id):
    """Get user info by ID"""
    user_info = load_user_info()
    return user_info.get(str(user_id), None)

def get_all_users():
    """Get all users with their info"""
    if os.path.exists(USER_INFO_FILE):
        with open(USER_INFO_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}