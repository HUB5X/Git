import os
import json

# --- TELEGRAM CONFIG ---
API_ID = 22009063
API_HASH = "fc7065f35831e39d77eccd52da1f4039"
SESSION_NAME = 'music'
BOT_TOKEN = '8188825085:AAFEFuZZL7nYsmzI2ToelQBbT6V9NHcZQvo' 
ADMIN_ID = 6646404639 

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'cards_v2.db')
SESSION_FILE_PATH = os.path.join(BASE_DIR, f'{SESSION_NAME}.session')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

# --- DYNAMIC SETTINGS MANAGER ---
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "monitored_channels": [-1002262145851],
            "result_channel": "@HUB2000X"
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f)
        return default_settings
    
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# Global Config Object
current_settings = load_settings()
MONITORED_CHANNELS = current_settings.get("monitored_channels", [])
RESULT_CHANNEL = current_settings.get("result_channel", "@HUB2000X")

def update_channels(channel_id, action="add"):
    global MONITORED_CHANNELS
    settings = load_settings()
    if action == "add" and channel_id not in settings["monitored_channels"]:
        settings["monitored_channels"].append(channel_id)
    elif action == "remove" and channel_id in settings["monitored_channels"]:
        settings["monitored_channels"].remove(channel_id)
    
    save_settings(settings)
    MONITORED_CHANNELS = settings["monitored_channels"]

def update_output(username):
    global RESULT_CHANNEL
    settings = load_settings()
    settings["result_channel"] = username
    save_settings(settings)
    RESULT_CHANNEL = username
