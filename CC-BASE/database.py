import sqlite3
from datetime import datetime
from config import DB_FILE

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_card TEXT UNIQUE,
            bin TEXT,
            country TEXT,
            country_flag TEXT,
            bank TEXT,
            type TEXT,
            level TEXT,
            brand TEXT,
            exp_month INTEGER,
            exp_year INTEGER,
            source TEXT,
            date_added TIMESTAMP
        )
    ''')
    # Add column if not exists (Migration for old DB)
    try:
        c.execute("ALTER TABLE cards ADD COLUMN country_flag TEXT")
    except:
        pass
    conn.commit()
    conn.close()

def add_card(full_card, bin_code, bin_data, month, year, source):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO cards (full_card, bin, country, country_flag, bank, type, level, brand, exp_month, exp_year, source, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (full_card, bin_code, bin_data['country'], bin_data.get('country_flag', ''), bin_data['bank'], bin_data['type'], 
              bin_data['level'], bin_data['brand'], int(month), int(year), source, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"DB Error: {e}")
        return False

def check_card_exists(full_card):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM cards WHERE full_card = ?", (full_card,))
    data = c.fetchone()
    conn.close()
    return data is not None

# --- ANALYTICS ---

def get_dashboard_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards")
    total_cards = c.fetchone()[0]
    
    # Get total unique BINs
    c.execute("SELECT COUNT(DISTINCT bin) FROM cards")
    total_bins = c.fetchone()[0]
    
    conn.close()
    return total_cards, total_bins

def get_country_stats_paginated(page=1, per_page=20):
    offset = (page - 1) * per_page
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get Stats: Country, Flag, Count
    c.execute('''
        SELECT country, country_flag, COUNT(*) as count 
        FROM cards 
        GROUP BY country 
        ORDER BY count DESC 
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    data = c.fetchall()
    
    # Get Total Countries count for pagination logic
    c.execute("SELECT COUNT(DISTINCT country) FROM cards")
    total_countries = c.fetchone()[0]
    
    conn.close()
    return data, total_countries

def get_cards_by_country(country_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card FROM cards WHERE country = ?", (country_name,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_cards_by_bin(bin_code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card FROM cards WHERE bin LIKE ?", (f"{bin_code}%",))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_bin_stats(bin_code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), country, bank, type, level, country_flag FROM cards WHERE bin LIKE ? GROUP BY bin LIMIT 1", (f"{bin_code}%",))
    data = c.fetchone()
    conn.close()
    if data:
        return {"count": data[0], "country": data[1], "bank": data[2], "type": data[3], "level": data[4], "flag": data[5]}
    return None

def delete_expired_cards():
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM cards WHERE exp_year < ?", (current_year,))
    c.execute("DELETE FROM cards WHERE exp_year = ? AND exp_month < ?", (current_year, current_month))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted
