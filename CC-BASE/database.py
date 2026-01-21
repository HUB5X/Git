import os
import sqlite3
from dotenv import load_dotenv

# --- LOAD ENV ---
load_dotenv()

# --- TELEGRAM CONFIG FROM ENV ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "music")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'cards_v2.db')
SESSION_FILE_PATH = os.path.join(BASE_DIR, f'{SESSION_NAME}.session')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')

if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Existing Cards Table
    c.execute('''CREATE TABLE IF NOT EXISTS cards 
                 (full_card TEXT PRIMARY KEY, bin TEXT, extra TEXT, month TEXT, year TEXT, source TEXT, date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # New Table: Monitored Channels (Stores ID and Name)
    c.execute('''CREATE TABLE IF NOT EXISTS monitored_channels 
                 (id INTEGER PRIMARY KEY, name TEXT)''')

    # New Table: Config (Stores Settings like Result Channel)
    c.execute('''CREATE TABLE IF NOT EXISTS config 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # Set Default Result Channel if not exists
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", ("result_channel", "@HUB2000X"))
    
    conn.commit()
    conn.close()

# Initialize DB tables on load
init_db()

# --- DYNAMIC SETTINGS MANAGERS (DB BASED) ---

def get_monitored_channels():
    """Returns a list of channel IDs for the scraper"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM monitored_channels")
    channels = [row[0] for row in c.fetchall()]
    conn.close()
    # Default ID if empty (example ID)
    if not channels:
        return [-1002262145851] 
    return channels

def get_monitored_channels_info():
    """Returns detailed list [(id, name), ...] for the UI"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM monitored_channels")
    data = c.fetchall()
    conn.close()
    return data

def get_result_channel():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", ("result_channel",))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "@HUB2000X"

# Global Variables (Accessed by main script)
MONITORED_CHANNELS = get_monitored_channels()
RESULT_CHANNEL = get_result_channel()

def update_channels(channel_id, action="add", channel_name="Unknown Channel"):
    global MONITORED_CHANNELS
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if action == "add":
        # Insert or Update the name if ID exists
        c.execute("INSERT OR REPLACE INTO monitored_channels (id, name) VALUES (?, ?)", (channel_id, channel_name))
    elif action == "remove":
        c.execute("DELETE FROM monitored_channels WHERE id=?", (channel_id,))
    
    conn.commit()
    conn.close()
    
    # Refresh Global List
    MONITORED_CHANNELS = get_monitored_channels()

def update_output(username):
    global RESULT_CHANNEL
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("result_channel", username))
    conn.commit()
    conn.close()
    RESULT_CHANNEL = username

# --- DASHBOARD & STATS FUNCTIONS ---
def get_dashboard_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards")
    total_cards = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT bin) FROM cards")
    total_bins = c.fetchone()[0]
    conn.close()
    return total_cards, total_bins

def delete_expired_cards():
    # Placeholder: Implement actual expiry logic based on 'month'/'year' columns if needed
    # For now returns 0
    return 0

def check_card_exists(full_card):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM cards WHERE full_card=?", (full_card,))
    exists = c.fetchone()
    conn.close()
    return exists is not None

def add_card(full_card, bin_code, extra, month, year, source):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO cards (full_card, bin, extra, month, year, source) VALUES (?, ?, ?, ?, ?, ?)",
                  (full_card, bin_code, str(extra), month, year, source))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# --- FILTER FUNCTIONS (Needed for bot_panel) ---
def get_country_stats_paginated(page, per_page=20):
    # This assumes you have logic to determine country from BIN or Extra
    # Since the original code implies this exists, I'll provide a basic implementation
    # querying the 'bin' column or however you stored country info.
    # Note: If you don't store country in DB, this needs to process raw data.
    # Here is a placeholder compatible structure:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # This is a simplified example. Adjust query if you have a 'country' column.
    # For now, we group by BIN as a proxy if country col doesn't exist, 
    # OR if you have a country column, change 'bin' to 'country'.
    c.execute("SELECT bin, COUNT(*) as count FROM cards GROUP BY bin ORDER BY count DESC") 
    all_data = c.fetchall()
    conn.close()
    
    total_items = len(all_data)
    start = (page - 1) * per_page
    end = start + per_page
    sliced_data = all_data[start:end]
    
    # Transform to expected format [(CountryName, Flag, Count)]
    # You might need your BIN lookup here to get Country Name from BIN
    result = []
    for row in sliced_data:
        bin_code, count = row
        # Placeholder names since we only have BIN in this basic table
        result.append((f"BIN: {bin_code}", "🏳️", count)) 
        
    return result, total_items

def get_cards_by_country(country_name):
    # Placeholder: Retrieve cards based on country name logic
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card FROM cards LIMIT 50") # Just returning sample
    cards = [row[0] for row in c.fetchall()]
    conn.close()
    return cards

def get_bin_stats(bin_code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards WHERE bin=?", (bin_code,))
    count = c.fetchone()[0]
    conn.close()
    # Mock return
    return {'count': count, 'country': 'Unknown', 'flag': '🏳️', 'bank': 'Unknown'}

def get_cards_by_bin(bin_code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card FROM cards WHERE bin=?", (bin_code,))
    cards = [row[0] for row in c.fetchall()]
    conn.close()
    return cards
