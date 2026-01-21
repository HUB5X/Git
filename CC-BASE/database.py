import sqlite3
import ast
import datetime
from typing import Dict, List, Tuple, Any

from config import DB_FILE, EXPORT_DIR, BOT_TOKEN, ADMIN_ID

# -----------------------
# DB INIT
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS cards (
            full_card TEXT PRIMARY KEY,
            bin TEXT,
            extra TEXT,
            month TEXT,
            year TEXT,
            source TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    # Monitored Channels (Stores ID and Name)
    c.execute(
        """CREATE TABLE IF NOT EXISTS monitored_channels (
            id INTEGER PRIMARY KEY,
            name TEXT
        )"""
    )
    
    # --- MIGRATION CHECK: Add 'name' column if missing ---
    try:
        c.execute("SELECT name FROM monitored_channels LIMIT 1")
    except sqlite3.OperationalError:
        print("🔧 Migrating Database: Adding 'name' column to monitored_channels...")
        try:
            c.execute("ALTER TABLE monitored_channels ADD COLUMN name TEXT DEFAULT 'Unknown Channel'")
        except Exception as e:
            print(f"Migration Failed: {e}")

    # Config (Stores settings like result_channel)
    c.execute(
        """CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )"""
    )

    # Default result_channel
    c.execute(
        "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
        ("result_channel", "@HUB2000X"),
    )

    conn.commit()
    conn.close()


# Initialize DB tables on import
init_db()


# -----------------------
# Helpers
# -----------------------
def _parse_extra(extra_text: str) -> Dict[str, Any]:
    """
    `extra` ကို DB ထဲမှာ str(dict) ပုံစံနဲ့ သိမ်းထားတဲ့အတွက်
    safe parse အတွက် ast.literal_eval သုံးပါတယ်။
    """
    if not extra_text:
        return {}
    try:
        obj = ast.literal_eval(extra_text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _now_ym() -> Tuple[int, int]:
    now = datetime.datetime.now()
    return now.year, now.month


def _is_expired(month_str: str, year_str: str, now_y: int, now_m: int) -> bool:
    try:
        m = int(str(month_str).strip())
        y = int(str(year_str).strip())
        if m < 1 or m > 12:
            return False
        # Expired if (year, month) < (now_year, now_month)
        return (y, m) < (now_y, now_m)
    except Exception:
        return False


# -----------------------
# Settings (DB-based)
# -----------------------
def get_monitored_channels() -> List[int]:
    """Returns a list of channel IDs for the scraper"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id FROM monitored_channels")
        channels = [row[0] for row in c.fetchall()]
        conn.close()

        # Default ID if empty (kept for backward compatibility)
        if not channels:
            return [-1002262145851]
        return channels
    except:
        return []


def get_monitored_channels_info() -> List[Tuple[int, str]]:
    """Returns detailed list [(id, name), ...] for the UI"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM monitored_channels ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return data


def update_channels(channel_id: int, action: str = "add", channel_name: str = "Unknown Channel") -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if action == "add":
        c.execute(
            "INSERT OR REPLACE INTO monitored_channels (id, name) VALUES (?, ?)",
            (int(channel_id), str(channel_name)),
        )
    elif action == "remove":
        c.execute("DELETE FROM monitored_channels WHERE id=?", (int(channel_id),))
    else:
        conn.close()
        raise ValueError("Invalid action. Use 'add' or 'remove'.")

    conn.commit()
    conn.close()


def get_result_channel() -> str:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", ("result_channel",))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "@HUB2000X"


def update_output(username: str) -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        ("result_channel", str(username).strip()),
    )
    conn.commit()
    conn.close()


# -----------------------
# Dashboard & Card Ops
# -----------------------
def get_dashboard_stats() -> Tuple[int, int]:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cards")
        total_cards = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT bin) FROM cards")
        total_bins = c.fetchone()[0]
        conn.close()
        return total_cards, total_bins
    except:
        return 0, 0


def delete_expired_cards() -> int:
    now_y, now_m = _now_ym()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card, month, year FROM cards")
    rows = c.fetchall()

    expired = []
    for full_card, month, year in rows:
        if _is_expired(month, year, now_y, now_m):
            expired.append(full_card)

    if expired:
        c.executemany("DELETE FROM cards WHERE full_card=?", [(x,) for x in expired])
        conn.commit()

    conn.close()
    return len(expired)


def check_card_exists(full_card: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM cards WHERE full_card=?", (full_card,))
    exists = c.fetchone()
    conn.close()
    return exists is not None


def add_card(full_card: str, bin_code: str, extra: Dict[str, Any], month: str, year: Any, source: str) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO cards (full_card, bin, extra, month, year, source) VALUES (?, ?, ?, ?, ?, ?)",
            (full_card, bin_code, str(extra), str(month), str(year), str(source)),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False
    except Exception as e:
        print(f"DB Error: {e}")
        return False


# -----------------------
# Filters / Export Helpers
# -----------------------
def get_country_stats_paginated(page: int, per_page: int = 20):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT extra FROM cards")
    rows = c.fetchall()
    conn.close()

    counter: Dict[str, Dict[str, Any]] = {}
    for (extra_text,) in rows:
        info = _parse_extra(extra_text)
        country = (info.get("country") or "Unknown").strip()
        flag = (info.get("country_flag") or "🏳️").strip()
        if country not in counter:
            counter[country] = {"count": 0, "flag": flag}
        counter[country]["count"] += 1
        # keep non-white flag if available
        if counter[country]["flag"] == "🏳️" and flag != "🏳️":
            counter[country]["flag"] = flag

    data_all = sorted(
        [(country, meta["flag"], meta["count"]) for country, meta in counter.items()],
        key=lambda x: x[2],
        reverse=True,
    )

    total = len(data_all)
    start = (page - 1) * per_page
    end = start + per_page
    return data_all[start:end], total


def get_cards_by_country(country_name: str) -> List[str]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card, extra FROM cards")
    rows = c.fetchall()
    conn.close()

    out = []
    target = (country_name or "").strip().lower()
    for full_card, extra_text in rows:
        info = _parse_extra(extra_text)
        ctry = (info.get("country") or "Unknown").strip().lower()
        if ctry == target:
            out.append(full_card)
    return out


def get_bin_stats(bin_code: str):
    bin_code = (bin_code or "").strip()[:6]
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards WHERE bin=?", (bin_code,))
    count = c.fetchone()[0]

    c.execute("SELECT extra FROM cards WHERE bin=? LIMIT 1", (bin_code,))
    row = c.fetchone()
    conn.close()

    info = _parse_extra(row[0]) if row else {}
    return {
        "count": count,
        "country": info.get("country", "Unknown"),
        "flag": info.get("country_flag", "🏳️"),
        "bank": info.get("bank", "Unknown"),
    }


def get_cards_by_bin(bin_code: str) -> List[str]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card FROM cards WHERE bin=?", ((bin_code or "").strip()[:6],))
    cards = [row[0] for row in c.fetchall()]
    conn.close()
    return cards
