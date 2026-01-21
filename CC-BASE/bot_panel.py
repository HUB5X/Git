import telebot
import os
import sys
import subprocess
import asyncio
import math
import time
import sqlite3 
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- IMPORT FROM DATABASE ---
from database import (
    BOT_TOKEN, ADMIN_ID, EXPORT_DIR, 
    update_channels, update_output, get_monitored_channels, 
    get_monitored_channels_info, get_dashboard_stats, delete_expired_cards,
    check_card_exists, add_card, 
    get_country_stats_paginated, get_cards_by_country, get_bin_stats, get_cards_by_bin,
    DB_FILE
)

# --- IMPORT FROM UTILS ---
# get_bin_details နဲ့ parse_expiry_year ကို ဒီကနေ ယူပါမယ်
from utils import card_pattern, get_flag_from_name, get_bin_details, parse_expiry_year

bot = telebot.TeleBot(BOT_TOKEN)

# Global Variables
main_client = None
main_loop = None
user_selection_cache = {}
dialog_cache = {} 

# --- CONFIGURATION ---
MAX_CONCURRENT_CHECKS = 5 

def set_main_client(client, loop):
    global main_client, main_loop
    main_client = client
    main_loop = loop

# --- GIT UPDATE HELPERS ---
def restart_program():
    """Script ကို Restart ချပေးမည့် Function"""
    python = sys.executable
    os.execl(python, python, *sys.argv)

def git_pull_update():
    """Git Pull လုပ်ပြီး Result ပြန်ပေးမည်"""
    try:
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

# --- UI HELPERS ---
def get_main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📊 Dashboard"),
        KeyboardButton("⚙️ Settings"),
        KeyboardButton("📂 File Tools"),
        KeyboardButton("🔍 Filter & Export"),
        KeyboardButton("📋 Channels"),
        KeyboardButton("❌ Close Panel")
    )
    return markup

# --- START & MAIN MENU ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(
        message.chat.id, 
        "👋 **Welcome to Pro Scraper V3.5 (Git Edition)**\n\nMain Menu ကို အောက်က Keyboard မှာ ရွေးချယ်နိုင်ပါပြီ:", 
        reply_markup=get_main_menu_keyboard(), 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "❌ Close Panel")
def close_panel(message):
    from telebot.types import ReplyKeyboardRemove
    bot.send_message(message.chat.id, "✅ Panel Closed. Type /start to open again.", reply_markup=ReplyKeyboardRemove())

# --- DASHBOARD ---
@bot.message_handler(func=lambda message: message.text == "📊 Dashboard")
def dashboard_view(message):
    if message.from_user.id != ADMIN_ID: return
    total_cards, total_bins = get_dashboard_stats()
    # Fetch count from DB
    monitored_list = get_monitored_channels()
    monitored_count = len(monitored_list)
    
    msg = (
        f"📊 **Live Dashboard**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 **Total Cards:** `{total_cards}`\n"
        f"🔢 **Unique BINs:** `{total_bins}`\n"
        f"📡 **Active Channels:** `{monitored_count}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Status: `Running`"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_dashboard"))
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "refresh_dashboard")
def refresh_dashboard(call):
    total_cards, total_bins = get_dashboard_stats()
    monitored_list = get_monitored_channels()
    monitored_count = len(monitored_list)
    msg = (
        f"📊 **Live Dashboard**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 **Total Cards:** `{total_cards}`\n"
        f"🔢 **Unique BINs:** `{total_bins}`\n"
        f"📡 **Active Channels:** `{monitored_count}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Status: `Running`"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_dashboard"))
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except: pass

# --- SETTINGS (WITH GIT UPDATE) ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Settings")
def settings_view(message):
    if message.from_user.id != ADMIN_ID: return
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📢 Set Output Channel", callback_data="set_output"),
        InlineKeyboardButton("🗑 Auto-Clean Expired Cards", callback_data="clean_expired"),
        InlineKeyboardButton("🔄 Update System (Git Pull)", callback_data="system_update")
    )
    bot.send_message(message.chat.id, "⚙️ **Settings & Maintenance**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "clean_expired")
def clean_expired_logic(call):
    deleted = delete_expired_cards()
    bot.answer_callback_query(call.id, f"🗑 Deleted {deleted} cards!")
    bot.send_message(call.message.chat.id, f"✅ **Cleanup Complete**\n🗑 Removed: `{deleted}` expired cards.")

@bot.callback_query_handler(func=lambda call: call.data == "system_update")
def system_update_handler(call):
    bot.edit_message_text("⏳ **Checking for updates...**\nRunning `git pull`...", call.message.chat.id, call.message.message_id)
    
    # Run Git Pull
    output = git_pull_update()
    
    if "Already up to date" in output:
        bot.edit_message_text(f"✅ **System is Up-to-Date!**\n\n`{output}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, f"✅ **Update Found & Downloaded!**\n\n`{output}`\n\n🔄 **Restarting Bot now...**", parse_mode="Markdown")
        time.sleep(2)
        restart_program() # Restart script

# --- FILTER & EXPORT ---
@bot.message_handler(func=lambda message: message.text == "🔍 Filter & Export")
def filter_view(message):
    if message.from_user.id != ADMIN_ID: return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🌎 By Country List", callback_data="country_page_1"),
        InlineKeyboardButton("🔢 By BIN", callback_data="filter_bin"),
        InlineKeyboardButton("📂 Export All Data", callback_data="export_all")
    )
    bot.send_message(message.chat.id, "🔍 **Select Filter Option:**", reply_markup=markup, parse_mode="Markdown")

# --- COUNTRY LIST (FLAG FIXED) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("country_page_"))
def country_list_view(call):
    page = int(call.data.split("_")[2])
    per_page = 20
    data, total_countries = get_country_stats_paginated(page, per_page)
    total_pages = math.ceil(total_countries / per_page)
    
    msg_text = f"🌎 **Top Countries (Page {page}/{total_pages})**\n━━━━━━━━━━━━━━━━━━\nမိမိလိုချင်သော နိုင်ငံ၏ **နံပါတ်စဉ်** ကို Reply ပြန်ပေးပါ။\n\n"
    user_id = call.from_user.id
    user_selection_cache[user_id] = {}
    
    for idx, (country, db_flag, count) in enumerate(data):
        display_flag = db_flag if (db_flag and db_flag != "🏳️") else get_flag_from_name(country)
        list_number = idx + 1 + (page-1)*per_page
        user_selection_cache[user_id][str(list_number)] = country
        msg_text += f"`{list_number}.` {display_flag} **{country}** : `{count}`\n"

    markup = InlineKeyboardMarkup(row_width=2)
    nav_btns = []
    if page > 1: nav_btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"country_page_{page-1}"))
    if page < total_pages: nav_btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"country_page_{page+1}"))
    if nav_btns: markup.add(*nav_btns)
        
    try: bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except: bot.send_message(call.message.chat.id, msg_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_country_selection(message):
    if message.from_user.id != ADMIN_ID: return
    user_id = message.from_user.id
    selected_num = message.text.strip()
    if user_id in user_selection_cache and selected_num in user_selection_cache[user_id]:
        country_name = user_selection_cache[user_id][selected_num]
        bot.reply_to(message, f"⏳ Exporting cards for **{country_name}**...")
        cards = get_cards_by_country(country_name)
        send_export_file(message.chat.id, cards, f"{country_name}")

# --- FILE TOOLS (SEMAPHORE / TURBO) ---
@bot.message_handler(func=lambda message: message.text == "📂 File Tools")
def file_tools_view(message):
    if message.from_user.id != ADMIN_ID: return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📤 Upload Combo File", callback_data="upload_req"))
    bot.send_message(message.chat.id, "📂 **File Processing Tools** (Turbo Mode)", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "upload_req")
def upload_prompt(call):
    try: msg = bot.edit_message_text("📤 **Please send the .txt file now:**", call.message.chat.id, call.message.message_id)
    except: msg = bot.send_message(call.message.chat.id, "📤 **Please send the .txt file now:**")
    bot.register_next_step_handler(msg, process_upload_step)

def process_upload_step(message):
    if not message.document:
        bot.reply_to(message, "❌ Invalid file.")
        return
    status_msg = bot.send_message(message.chat.id, "⏳ **Reading File...**")
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    temp_path = "temp_combo.txt"
    with open(temp_path, 'wb') as new_file: new_file.write(downloaded_file)
    asyncio.run_coroutine_threadsafe(process_bulk_upload_concurrent(message.chat.id, status_msg.message_id, temp_path), main_loop)

async def process_bulk_upload_concurrent(chat_id, message_id, file_path):
    import aiohttp
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        matches = card_pattern.findall(content)
    os.remove(file_path)
    
    total = len(matches)
    if total == 0:
        bot.edit_message_text("❌ No cards found.", chat_id, message_id)
        return

    # Shared Counters
    stats = {"checked": 0, "added": 0, "duplicates": 0}
    
    # Semaphore to limit concurrency
    sem = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
    
    async def check_single_card(session, match):
        async with sem: # Only allow 5 at a time
            full_card = f"{match[0].replace(' ', '').replace('-', '')}|{match[1]}|{match[2]}|{match[3] if match[3] else 'N/A'}"
            
            if check_card_exists(full_card):
                stats["duplicates"] += 1
            else:
                bin_data = await get_bin_details(session, full_card)
                parts = full_card.split('|')
                year = parse_expiry_year(parts[2])
                month = parts[1]
                
                if add_card(full_card, full_card[:6], bin_data, month, year, "File Upload"):
                    stats["added"] += 1
            
            stats["checked"] += 1
            
            # Update UI every 10 cards
            if stats["checked"] % 10 == 0 or stats["checked"] == total:
                percent = int((stats["checked"] / total) * 100)
                filled = int(10 * (stats["checked"] / total))
                bar = "█" * filled + "░" * (10 - filled)
                try:
                    bot.edit_message_text(
                        f"🚀 **Turbo Checking...**\n"
                        f"`{bar}` **{percent}%**\n\n"
                        f"🔢 Checked: `{stats['checked']}/{total}`\n"
                        f"✅ Added: `{stats['added']}`\n"
                        f"♻️ Duplicates: `{stats['duplicates']}`",
                        chat_id, message_id, parse_mode="Markdown"
                    )
                except: pass

    # Run Tasks
    async with aiohttp.ClientSession() as session:
        tasks = [check_single_card(session, match) for match in matches]
        await asyncio.gather(*tasks)

    # Final Message
    bot.edit_message_text(
        f"✅ **Turbo Upload Complete!**\n━━━━━━━━━━━━━━━━━━\n"
        f"📥 Total: `{total}`\n"
        f"✅ Added: `{stats['added']}`\n"
        f"♻️ Duplicates: `{stats['duplicates']}`", 
        chat_id, message_id, parse_mode="Markdown"
    )

# --- CHANNEL MANAGER & PAGINATION LOGIC ---

@bot.message_handler(func=lambda message: message.text == "📋 Channels")
def channel_manager_view(message):
    if message.from_user.id != ADMIN_ID: return
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("➕ Add New Channel", callback_data="add_channel_menu"),
        InlineKeyboardButton("📋 View/Remove Channels", callback_data="list_remove_channels")
    )
    bot.send_message(message.chat.id, "📡 **Channel Manager**", reply_markup=markup, parse_mode="Markdown")

# -- Remove Channel Logic (UPDATED TO SHOW NAMES) --
@bot.callback_query_handler(func=lambda call: call.data == "list_remove_channels")
def list_remove_channels(call):
    # Fetch details from DB instead of global list to get Names
    channels_info = get_monitored_channels_info() # Returns [(id, name), ...]
    
    if not channels_info:
        bot.answer_callback_query(call.id, "No channels active.")
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for cid, cname in channels_info:
        # Display Name first, then ID.
        # Truncate long names
        safe_name = cname[:20] + "..." if len(cname) > 20 else cname
        btn_text = f"🗑 {safe_name}" 
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"rem_{cid}"))
        
    bot.edit_message_text("📋 **Tap to Remove Channel:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rem_"))
def remove_channel_action(call):
    cid = int(call.data.split("_")[1])
    update_channels(cid, action="remove")
    bot.answer_callback_query(call.id, "Removed!")
    list_remove_channels(call) # Refresh list

# -- Add Channel Menu --
@bot.callback_query_handler(func=lambda call: call.data == "add_channel_menu")
def add_channel_menu(call):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔗 Enter ID / Link", callback_data="add_by_link"),
        InlineKeyboardButton("📂 Select from Joined List", callback_data="add_from_list")
    )
    bot.edit_message_text("📌 **How do you want to add?**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# -- Add by Link --
@bot.callback_query_handler(func=lambda call: call.data == "add_by_link")
def add_by_link_prompt(call):
    msg = bot.send_message(call.message.chat.id, "🔗 **Enter Channel/Group Link or ID:**")
    bot.register_next_step_handler(msg, process_add_link)

def process_add_link(message):
    link = message.text.strip()
    bot.send_message(message.chat.id, "⏳ **Resolving Link...**")
    asyncio.run_coroutine_threadsafe(resolve_and_add_channel(message.chat.id, link), main_loop)

async def resolve_and_add_channel(chat_id, link):
    try:
        try: entity = int(link)
        except: entity = link 
        chat = await main_client.get_entity(entity)
        
        # Save Name along with ID
        update_channels(chat.id, action="add", channel_name=chat.title)
        
        bot.send_message(chat_id, f"✅ **Added:** {chat.title}\nID: `{chat.id}`")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Failed: {e}")

# -- Add from List (WITH PAGINATION) --
@bot.callback_query_handler(func=lambda call: call.data == "add_from_list")
def add_from_list_init(call):
    bot.edit_message_text("⏳ **Fetching all your channels...**\n(This might take a few seconds)", call.message.chat.id, call.message.message_id)
    # Start fetching all dialogs
    asyncio.run_coroutine_threadsafe(fetch_all_dialogs(call.message.chat.id), main_loop)

async def fetch_all_dialogs(chat_id):
    try:
        # Fetch unlimited dialogs (or a safe high limit like 500)
        dialogs = await main_client.get_dialogs(limit=None) 
        
        # Filter only Groups and Channels
        channel_list = []
        for d in dialogs:
            if d.is_group or d.is_channel:
                channel_list.append({"id": d.id, "title": d.title})
        
        # Save to Cache
        dialog_cache[chat_id] = channel_list
        
        # Show Page 1
        show_dialog_page(chat_id, 1)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {e}")

def show_dialog_page(chat_id, page):
    if chat_id not in dialog_cache:
        bot.send_message(chat_id, "❌ Session expired. Please fetch again.")
        return

    items = dialog_cache[chat_id]
    per_page = 20
    total_pages = math.ceil(len(items) / per_page)
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_items = items[start_idx:end_idx]
    
    # Get currently monitored IDs for checking (to show checkmark)
    current_monitored_ids = get_monitored_channels()

    markup = InlineKeyboardMarkup(row_width=2)
    
    # Generate Channel Buttons
    for item in current_items:
        # Check if already added
        status = "✅" if item['id'] in current_monitored_ids else ""
        btn_text = f"{status} {item['title'][:20]}" # Truncate title
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"save_id_{item['id']}_{page}"))
        
    # Navigation Buttons
    nav_btns = []
    if page > 1:
        nav_btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"dlg_page_{page-1}"))
    if page < total_pages:
        nav_btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"dlg_page_{page+1}"))
    if nav_btns:
        markup.add(*nav_btns)
        
    # Back Button
    markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="add_channel_menu"))

    msg_text = f"📂 **Select Channel to Monitor (Page {page}/{total_pages}):**\nFound Total: {len(items)}"
    
    # Try to edit, if fails send new
    try:
        bot.edit_message_text(msg_text, chat_id, message_id=None, reply_markup=markup) 
        pass
    except:
        bot.send_message(chat_id, msg_text, reply_markup=markup)

# Helper wrapper for callback-based page switching
@bot.callback_query_handler(func=lambda call: call.data.startswith("dlg_page_"))
def dialog_page_switch(call):
    page = int(call.data.split("_")[2])
    show_dialog_page(call.message.chat.id, page)

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_id_"))
def save_channel_id(call):
    parts = call.data.split("_")
    new_id = int(parts[2])
    current_page = int(parts[3])
    
    # Need to find the name from cache to save it properly
    chat_id = call.message.chat.id
    channel_name = "Unknown Channel"
    
    if chat_id in dialog_cache:
        for item in dialog_cache[chat_id]:
            if item['id'] == new_id:
                channel_name = item['title']
                break

    update_channels(new_id, action="add", channel_name=channel_name)
    bot.answer_callback_query(call.id, "✅ Added!")
    
    # Stay on the same page and refresh to show checkmark
    show_dialog_page(chat_id, current_page)

# --- UTILS ---
def send_export_file(chat_id, cards, name):
    if not cards: return
    path = os.path.join(EXPORT_DIR, f"{name}.txt")
    with open(path, "w") as f: f.write("\n".join(cards))
    with open(path, "rb") as f: bot.send_document(chat_id, f, caption=f"📂 {len(cards)} Cards ({name})")
    os.remove(path)

@bot.callback_query_handler(func=lambda call: call.data == "set_output")
def set_output_prompt(call):
    msg = bot.send_message(call.message.chat.id, "📢 **Enter Output Channel Username:**")
    bot.register_next_step_handler(msg, process_set_output)

def process_set_output(message):
    update_output(message.text)
    bot.send_message(message.chat.id, f"✅ Output Channel set to: {message.text}")

@bot.callback_query_handler(func=lambda call: call.data == "filter_bin")
def filter_bin_prompt(call):
    msg = bot.send_message(call.message.chat.id, "🔢 **Enter BIN Code:**")
    bot.register_next_step_handler(msg, process_bin_lookup)

def process_bin_lookup(message):
    bin_code = message.text.strip()[:6]
    stats = get_bin_stats(bin_code)
    if stats and stats['count'] > 0:
        flag = stats['flag'] if stats['flag'] else "🏳️"
        msg = f"🔍 **BIN Found**\n🔢 `{bin_code}`\n📊 `{stats['count']}`\n{flag} {stats['country']}\n🏦 {stats['bank']}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"📥 Export", callback_data=f"do_export_bin_{bin_code}"))
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"❌ No cards for `{bin_code}`.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_export_bin_"))
def do_export_bin(call):
    bin_code = call.data.split("_")[3]
    cards = get_cards_by_bin(bin_code)
    send_export_file(call.message.chat.id, cards, f"BIN_{bin_code}")

@bot.callback_query_handler(func=lambda call: call.data == "export_all")
def export_all_data(call):
    bot.answer_callback_query(call.id, "Generating...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_card FROM cards")
    cards = [r[0] for r in c.fetchall()]
    conn.close()
    send_export_file(call.message.chat.id, cards, "All_Cards")

def run_bot_polling():
    bot.infinity_polling()
