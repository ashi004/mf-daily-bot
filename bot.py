import requests
import os
import json
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from fetcher import generate_report

load_dotenv()

# --- ⚠️ SAFETY SWITCH ⚠️ ---
TEST_MODE = True  # Set False when ready to go live

def send_telegram_msg():
    token = os.getenv("TELEGRAM_TOKEN")
    
    if TEST_MODE:
        print("🚧 TEST MODE ON")
        chat_id = os.getenv("TEST_CHANNEL_ID") 
    else:
        print("🔴 LIVE MODE")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Error: Missing Credentials")
        return

    # 1. Generate Report
    day_index = datetime.today().weekday()
    if day_index >= 5:
        final_msg = generate_report(report_type="weekly")
    else:
        final_msg = generate_report(report_type="daily")

    # --- 2. Create the "Invite" Content ---
    invite_link = "https://t.me/+wjibPaNXP-xjZTE1"
    
    invite_pitch = (
        "🚀 *Start tracking your Wealth!* \n\n"
        "Get daily Nifty updates, Mutual Fund tracking, and Gold rates automatically on Telegram.\n\n"
        "👇 *Join Nivesh Niti here (It's Free):*"
    )
    
    # FIX: We add safe='' to force encoding of everything, including '/' and '+'
    # This ensures the '+' becomes '%2B' and survives the trip to WhatsApp
    enc_pitch = urllib.parse.quote(invite_pitch)
    enc_link = urllib.parse.quote(invite_link, safe='') 

    # Links
    wa_url = f"https://api.whatsapp.com/send?text={enc_pitch}%0A{enc_link}"
    tg_url = f"https://t.me/share/url?url={invite_link}&text={enc_pitch}"

    # --- 3. Layout ---
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Share on WhatsApp 🟢", "url": wa_url},
                {"text": "Share on Telegram ✈️", "url": tg_url}
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": final_msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    
    try:
        requests.post(url, json=payload)
        print("✅ Message Sent!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_telegram_msg()