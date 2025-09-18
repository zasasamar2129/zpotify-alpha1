# -*- coding: utf-8 -*-

import os
import json
import subprocess
import psutil
import time
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import speedtest
from datetime import datetime
from user_info import get_all_users, update_user_info, get_user_info
from functools import lru_cache
from datetime import datetime, timedelta
from config import BOT_PATH, CONFIG_ENV_PATH, USER_INFO_PATH, MAINTENANCE_FILE, BAN_LIST_FILE
from flask import jsonify
from dotenv import load_dotenv
LOG_FILE = os.path.join(BOT_PATH, 'bot.log')
DB_FOLDER = "database"
load_dotenv(CONFIG_ENV_PATH)
# Initialize Flask app
app = Flask(__name__)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}


# Shared languages dictionary
LANGUAGES = {
    "en": "English",
    "fa": "فارسی",
    "es": "Español",
    "ru": "Русский",
    "ar": "عربی",
    "hi": "हिन्दी"
}

app.secret_key = os.environ.get('WEB_ADMIN_SECRET_KEY', 'your-secret-key-here')

# Configuration
app.config.from_pyfile('config.py')

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for authentication
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Mock user database (replace with real database in production)
users = {
    'admin': {'password': generate_password_hash('admin')}
}

from datetime import datetime
from flask import Flask
import humanize

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value == 'Never':
        return value
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f').strftime(format)

@app.template_filter('timeago')
def timeago_filter(value):
    if value == 'Never':
        return ''
    now = datetime.now()
    then = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
    return humanize.naturaltime(now - then)


@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

# Helper functions
def get_bot_status():
    try:
        # More reliable process check
        result = subprocess.run(
            ['pgrep', '-f', 'python3 -m mbot'],
            cwd=BOT_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return bool(result.stdout.decode().strip())
    except Exception as e:
        app.logger.error(f"Status check error: {str(e)}")
        return False

def get_system_stats():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    
    # Enhanced bot status check
    bot_running = get_bot_status()
    bot_pid = None
    if bot_running:
        try:
            result = subprocess.run(['pgrep', '-f', 'python3 -m mbot'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
            bot_pid = result.stdout.decode().strip()
        except:
            pass
    
    return {
        'cpu': cpu,
        'memory': memory.percent,
        'memory_total': round(memory.total / (1024 ** 3)),
        'memory_used': round(memory.used / (1024 ** 3)),
        'disk': disk.percent,
        'disk_total': round(disk.total / (1024 ** 3)),
        'disk_used': round(disk.used / (1024 ** 3)),
        'boot_time': boot_time,
        'bot_running': bot_running,
        'bot_pid': bot_pid
    }

# In app.py, modify the get_network_speed() function:
# Global variable to cache results
last_speedtest = None
speedtest_cache = {'download': 0, 'upload': 0, 'ping': 0}
@lru_cache(maxsize=1)
def get_network_speed():
    global last_speedtest, speedtest_cache
    
    # Only run actual speedtest once every 30 minutes
    if last_speedtest is None or (datetime.now() - last_speedtest) > timedelta(minutes=30):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            st.timeout = 10
            
            speedtest_cache['download'] = round(st.download() / 10**6, 2)
            speedtest_cache['upload'] = round(st.upload() / 10**6, 2)
            speedtest_cache['ping'] = round(st.results.ping, 2)
            
            last_speedtest = datetime.now()
        except Exception as e:
            app.logger.warning(f"Speedtest failed, using cached values: {str(e)}")
    
    return speedtest_cache

def get_bot_stats():
    user_info = get_all_users()
    return {
        'total_users': len(user_info),  # Count users from user_info.json
        'active_today': 0,  # Placeholder (update logic if needed)
        'files_served': 0,  # Placeholder
        'banned_users': len(get_ban_list())
    }


def get_ban_list():
    ban_file = os.path.join(DB_FOLDER, "banned_users.json")
    if os.path.exists(ban_file):
        with open(ban_file, 'r') as f:
            return json.load(f)
    return []

def get_maintenance_status():
    maint_file = os.path.join(DB_FOLDER, 'maintenance_status.json')
    if os.path.exists(maint_file):
        with open(maint_file, 'r') as f:
            return json.load(f).get('maintenance', False)
    return False

def get_logs(lines=100):
    log_file = os.path.join(BOT_PATH, 'bot.log')
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                return ''.join(f.readlines()[-lines:])
        except Exception as e:
            return f"Error reading logs: {str(e)}"
    return "No logs found at " + log_file

def get_config():
    if os.path.exists(CONFIG_ENV_PATH):
        with open(CONFIG_ENV_PATH, 'r') as f:
            return f.read()
    return f"Config file not found at {CONFIG_ENV_PATH}"

def update_config(new_config):
    with open(CONFIG_ENV_PATH, 'w') as f:
        f.write(new_config)

def get_text_customizations():
    text_file = 'text_customizations.json'
    if os.path.exists(text_file):
        with open(text_file, 'r') as f:
            return json.load(f)
    return {}

def update_text_customizations(new_texts):
    text_file = 'text_customizations.json'
    with open(text_file, 'w') as f:
        json.dump(new_texts, f)



# Routes
@app.route('/')
def home():
    return render_template('home.html', now=datetime.now())

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@login_required
def dashboard():
    stats = get_system_stats()
    network = get_network_speed()
    bot_stats = get_bot_stats()
    maintenance = get_maintenance_status()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         network=network,
                         bot_stats=bot_stats,
                         maintenance=maintenance)

# Add these API endpoints to app.py

@app.route('/api/dashboard_data')
@login_required
def api_dashboard_data():
    """Combined endpoint for all dashboard data"""
    return jsonify({
        'system_stats': get_system_stats(),
        'network_speed': get_network_speed(),
        'bot_stats': get_bot_stats(),
        'maintenance': get_maintenance_status(),
        'bot_status': get_bot_status()
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and check_password_hash(users[username]['password'], password):
            user = User(username)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = get_system_stats()
    network = get_network_speed()
    bot_stats = get_bot_stats()
    maintenance = get_maintenance_status()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         network=network,
                         bot_stats=bot_stats,
                         maintenance=maintenance)
import json
with open(USER_INFO_PATH, 'r') as f:
    print(json.load(f))  # Should show your user 
    
@app.route('/users')
@login_required
def users_page():
    """Load and display users with real-time status"""
    try:
        with open(USER_INFO_PATH, 'r') as f:
            users_data = json.load(f)
        
        # Get banned users for status checking
        banned_users = get_ban_list()
        
        users = []
        for user_id, data in users_data.items():
            # Determine real-time status (override from banned list)
            status = 'banned' if user_id in banned_users else data.get('status', 'active')
            
            users.append({
                'id': user_id,
                'username': data.get('username', 'N/A'),
                'first_name': data.get('first_name', 'N/A'),
                'last_name': data.get('last_name', 'N/A'),
                'status': status,  # Real-time status
                'last_active': data.get('last_active', 'Never'),
                'notes': data.get('notes', '')
            })
        
        return render_template('users.html', users=users)
        
    except Exception as e:
        flash(f"Error loading user data: {str(e)}", "danger")
        return render_template('users.html', users=[])

@app.route('/debug_users')
@login_required
def debug_users():
    """Debug endpoint to see raw user data"""
    try:
        with open(USER_INFO_PATH, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if request.method == 'POST':
        data = {
            'first_name': request.form.get('first_name', ''),
            'last_name': request.form.get('last_name', ''),
            'username': request.form.get('username', ''),
            'notes': request.form.get('notes', ''),
            'status': request.form.get('status', 'active'),
            'updated_at': datetime.now().isoformat()  # Add timestamp
        }
        
        # Save to user_info.json
        update_user_info(user_id, data)
        flash('User information updated successfully!', 'success')
        return redirect(url_for('users_page'))
    
    # Load existing data
    user_data = get_user_info(user_id) or {'id': user_id}
    return render_template('edit_user.html', user=user_data)

@app.route('/ban', methods=['GET', 'POST'])
@login_required
def ban_management():
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        
        ban_list = get_ban_list()
        
        if action == 'ban' and user_id not in ban_list:
            ban_list.append(user_id)
            with open(BAN_LIST_FILE, 'w') as f:
                json.dump(ban_list, f)
            
            # Update user status in user_info.json
            update_user_info(user_id, {'status': 'banned'})
            flash(f'User {user_id} banned successfully', 'success')
            
        elif action == 'unban' and user_id in ban_list:
            ban_list.remove(user_id)
            with open('banned_users.json', 'w') as f:
                json.dump(ban_list, f)
            
            # Update user status in user_info.json
            update_user_info(user_id, {'status': 'active'})
            flash(f'User {user_id} unbanned successfully', 'success')
        
        return redirect(url_for('ban_management'))
    
    ban_list = get_ban_list()
    return render_template('ban.html', banned_users=ban_list)

@app.route('/maintenance', methods=['GET', 'POST'])
@login_required
def maintenance():
    if request.method == 'POST':
        status = request.form.get('status') == 'true'
        with open(MAINTENANCE_FILE, 'w') as f:
            json.dump({'maintenance': status}, f)
        flash('Maintenance mode updated successfully')
        return redirect(url_for('maintenance'))
    
    current_status = get_maintenance_status()
    return render_template('maintenance.html', status=current_status)

# Add these helper functions to app.py

def start_bot_process():
    """Start the bot process in a new session"""
    try:
        process = subprocess.Popen(
            ['python3', '-m', 'mbot'],
            cwd=BOT_PATH,  # Set working directory
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        return True
    except Exception as e:
        app.logger.error(f"Failed to start bot: {str(e)}")
        return False

def force_kill_bot():
    """Forcefully kill the bot process"""
    try:
        # Kill the entire process group
        subprocess.run(['pkill', '-9', '-f', 'python3 -m mbot'], timeout=10)
        time.sleep(1)  # Give it time to terminate
        return True
    except Exception as e:
        app.logger.error(f"Force kill failed: {str(e)}")
        return False

# Update the bot_control route
@app.route('/bot_control', methods=['GET', 'POST'])
@login_required
def bot_control():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'start':
            if get_bot_status():
                flash('Bot is already running!', 'warning')
            else:
                if start_bot_process():
                    flash('Bot started successfully!', 'success')
                else:
                    flash('Failed to start bot', 'danger')
                    
        elif action == 'restart':
            try:
                # First try normal shutdown
                if get_bot_status():
                    subprocess.run(['pkill', '-f', 'python3 -m mbot'], timeout=10)
                    time.sleep(2)  # Give it time to shutdown
                
                # Check if process is still running
                time.sleep(1)  # Additional delay
                if get_bot_status():
                    force_kill_bot()
                    time.sleep(1)
                
                # Start new process only if we intended to restart
                if not get_bot_status():  # Ensure it's actually stopped before starting
                    if start_bot_process():
                        flash('Bot restarted successfully!', 'success')
                    else:
                        flash('Restart failed - could not start bot', 'danger')
                else:
                    flash('Failed to stop bot during restart', 'danger')
            except Exception as e:
                app.logger.error(f"Restart failed: {str(e)}")
                flash(f'Restart failed: {str(e)}', 'danger')
                
        elif action == 'shutdown':
            try:
                if get_bot_status():
                    # First try normal shutdown
                    subprocess.run(['pkill', '-f', 'python3 -m mbot'], timeout=10)
                    time.sleep(2)
                    
                    # Check if still running after normal shutdown
                    if get_bot_status():
                        force_kill_bot()
                        time.sleep(1)
                        if not get_bot_status():
                            flash('Bot forcefully terminated!', 'warning')
                        else:
                            flash('Failed to terminate bot!', 'danger')
                    else:
                        flash('Bot shutdown successfully!', 'success')
                else:
                    flash('Bot is not running', 'info')
            except Exception as e:
                app.logger.error(f"Shutdown failed: {str(e)}")
                flash(f'Shutdown failed: {str(e)}', 'danger')
                
        elif action == 'force_kill':
            try:
                if get_bot_status():
                    if force_kill_bot():
                        flash('Bot forcefully terminated!', 'warning')
                    else:
                        flash('Force kill failed', 'danger')
                else:
                    flash('Bot is not running', 'info')
            except Exception as e:
                flash(f'Force kill error: {str(e)}', 'danger')
                
        elif action == 'clear_session':
            try:
                session_file = os.path.join(BOT_PATH, 'session.session')
                if os.path.exists(session_file):
                    os.remove(session_file)
                    flash('Session file cleared successfully!', 'success')
                else:
                    flash('No session file found', 'info')
            except Exception as e:
                flash(f'Error clearing session: {str(e)}', 'danger')
                
        return redirect(url_for('bot_control'))
    
    stats = get_system_stats()
    return render_template('bot_control.html', stats=stats)

@app.route('/api/logs')
@login_required
def api_logs():
    log_content = get_logs()
    return log_content

@app.route('/admin_manage', methods=['GET', 'POST'])
@login_required
def admin_manage():
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        
        # Load current sudo users from config
        config = get_config()
        lines = config.split('\n')
        
        if action == 'add':
            # Add user to SUDO_USERS in config
            for i, line in enumerate(lines):
                if line.startswith('SUDO_USERS='):
                    current_users = line.split('=')[1].strip().split(',')
                    if user_id not in current_users:
                        current_users.append(user_id)
                        lines[i] = f"SUDO_USERS={','.join(current_users)}"
                        update_config('\n'.join(lines))
                        flash(f'User {user_id} added to sudo users')
                    else:
                        flash(f'User {user_id} is already a sudo user')
                    break
        elif action == 'remove':
            # Remove user from SUDO_USERS in config
            for i, line in enumerate(lines):
                if line.startswith('SUDO_USERS='):
                    current_users = line.split('=')[1].strip().split(',')
                    if user_id in current_users:
                        current_users.remove(user_id)
                        lines[i] = f"SUDO_USERS={','.join(current_users)}"
                        update_config('\n'.join(lines))
                        flash(f'User {user_id} removed from sudo users')
                    else:
                        flash(f'User {user_id} is not a sudo user')
                    break
        
        return redirect(url_for('admin_manage'))
    
    # Get current sudo users from config
    config = get_config()
    sudo_users = []
    for line in config.split('\n'):
        if line.startswith('SUDO_USERS='):
            sudo_users = line.split('=')[1].strip().split(',')
            break
    
    return render_template('admin_manage.html', sudo_users=sudo_users)

@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    if request.method == 'POST':
        message = request.form.get('message')
        user_list = get_user_list()
        
        # In a real implementation, you would send this to your bot's broadcast endpoint
        # For this example, we'll just save it to a file
        with open('pending_broadcast.txt', 'w') as f:
            f.write(message)
        
        flash(f'Broadcast message prepared for {len(user_list)} users')
        return redirect(url_for('broadcast'))
    
    return render_template('broadcast.html')

@app.route('/language', methods=['GET', 'POST'])
@login_required
def language_management():
    languages = {
        "en": "English",
        "fa": "فارسی",
        "es": "Español",
        "ru": "Русский",
        "ar": "عربی",
        "hi": "हिन्दी"
    }
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'set_global':
            lang = request.form.get('language')
            # Implement global language setting logic
            flash(f'Global language set to {languages.get(lang, lang)}')
        elif action == 'set_user':
            user_id = request.form.get('user_id')
            lang = request.form.get('language')
            # Implement user-specific language setting logic
            flash(f'Language for user {user_id} set to {languages.get(lang, lang)}')
        
        return redirect(url_for('language_management'))
    
    return render_template('language.html', languages=languages)

@app.route('/logs')
@login_required
def logs():
    log_content = get_logs()
    return render_template('logs.html', logs=log_content)

@app.route('/monitoring')
@login_required
def monitoring():
    stats = get_system_stats()
    network = get_network_speed()
    return render_template('monitoring.html', stats=stats, network=network)

@app.route('/config', methods=['GET', 'POST'])
@login_required
def config_editor():
    if request.method == 'POST':
        new_config = request.form.get('config')
        update_config(new_config)
        flash('Configuration updated successfully')
        return redirect(url_for('config_editor'))
    
    config_content = get_config()
    return render_template('config.html', config=config_content)

@app.route('/text_customization', methods=['GET', 'POST'])
@login_required
def text_customization():
    if request.method == 'POST':
        new_texts = {}
        for key in request.form:
            if key != 'submit':
                new_texts[key] = request.form.get(key)
        
        update_text_customizations(new_texts)
        flash('Text customizations updated successfully')
        return redirect(url_for('text_customization'))
    
    texts = get_text_customizations()
    return render_template('text_customization.html', texts=texts, languages=LANGUAGES)

# API Endpoints
@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify(get_system_stats())

@app.route('/api/network')
@login_required
def api_network():
    return jsonify(get_network_speed())

@app.route('/api/bot_status')
@login_required
def api_bot_status():
    return jsonify({'running': get_bot_status()})

# Static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Schedule periodic tasks
    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.add_job(get_system_stats, 'interval', minutes=1)
    scheduler.add_job(get_network_speed, 'interval', minutes=5)
    scheduler.start()
    
    app.run(host='0.0.0.0', port=3000, debug=True)