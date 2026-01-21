import asyncio
import threading
import os
import sys
import time
import aiohttp
from telethon import TelegramClient, events, errors
from config import *
from database import init_db, add_card, check_card_exists
from utils import card_pattern, get_bin_details, parse_expiry_year
from bot_panel import run_bot_polling, bot, set_main_client # Import Connector

init_db()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

client = TelegramClient(SESSION_FILE_PATH, API_ID, API_HASH, loop=loop)

# Inject Client into Bot Panel
set_main_client(client, loop)

async def process_card_event(full_card, source_title):
    if check_card_exists(full_card): return

    async with aiohttp.ClientSession() as session:
        bin_data = await get_bin_details(session, full_card)
        
        parts = full_card.split('|')
        year = parse_expiry_year(parts[2])
        month = parts[1]
        
        saved = add_card(full_card, full_card[:6], bin_data, month, year, source_title)
        
        if saved:
            msg = (
                f"🔍 **New Card Found**\n\n"
                f"💳 `{full_card}`\n"
                f"🏳️ {bin_data['country']} {bin_data['country_flag']}\n"
                f"🏦 {bin_data['bank']}\n"
                f"📅 Exp: {month}/{year}\n"
                f"📢 Source: `{source_title}`"
            )
            try:
                # Load latest result channel
                from config import RESULT_CHANNEL 
                await client.send_message(RESULT_CHANNEL, msg)
                print(f"✅ Sent: {full_card}")
            except Exception as e:
                print(f"Send Error: {e}")

@client.on(events.NewMessage())
async def handler(event):
    # Load latest channels
    from config import MONITORED_CHANNELS
    
    if event.chat_id not in MONITORED_CHANNELS:
        return

    message = event.message.message or ""
    matches = card_pattern.findall(message)
    
    for match in matches:
        cc_num = match[0].replace(' ', '').replace('-', '')
        month = match[1]
        year = match[2]
        cvv = match[3] if match[3] else 'N/A'
        
        if len(year) == 2: year = "20" + year
            
        full_card = f"{cc_num}|{month}|{year}|{cvv}"
        await process_card_event(full_card, event.chat.title or "Unknown")

async def main():
    print("🕵️ Scraper Started...")
    await client.start()
    print("✅ Client Online.")
    
    try:
        bot.send_message(ADMIN_ID, "🚀 **System Online!**")
    except: pass
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Start Bot Panel
    t = threading.Thread(target=run_bot_polling, daemon=True)
    t.start()
    
    # Start Scraper
    while True:
        try:
            loop.run_until_complete(main())
        except errors.AuthKeyUnregisteredError:
            print("❌ Session Invalid. Deleting...")
            if os.path.exists(SESSION_FILE_PATH):
                os.remove(SESSION_FILE_PATH)
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Critical Error: {e}")
            time.sleep(10)
