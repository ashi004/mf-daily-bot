import requests
import os
import json
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from fetcher import generate_report

load_dotenv()

# --- 🚀 LIVE DEPLOYMENT SWITCH 🚀 ---
TEST_MODE = False  # Set to False to post to Nivesh Niti Daily

def send_telegram_msg():
    token = os.getenv("TELEGRAM_TOKEN")
    
    if TEST_MODE:
        print("🚧 TEST MODE: Sending to Test Lab")
        chat_id = os.getenv("TEST_CHANNEL_ID") 
    else:
        print("🔴 LIVE MODE: Sending to Nivesh Niti Daily")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Error: Missing Credentials in .env")
        return

    # 1. Generate the Report (Automatically handles Daily vs Weekly)
    try:
        final_msg = generate_report()
    except Exception as e:
        print(f"❌ Fetcher Error: {e}")
        return

    # --- 2. Smart Invite Content (Growth Strategy) ---
    invite_link = "https://t.me/+wjibPaNXP-xjZTE1"
    invite_pitch = (
        "🚀 *Start tracking your Wealth!* \n\n"
        "Get daily Nifty updates, Mutual Fund tracking, and Gold rates automatically on Telegram.\n\n"
        "👇 *Join Nivesh Niti here (It's Free):*"
    )
    
    # Safe encoding for the plus sign survival
    enc_pitch = urllib.parse.quote(invite_pitch)
    enc_link = urllib.parse.quote(invite_link, safe='') 

    # Share URLs
    wa_url = f"https://api.whatsapp.com/send?text={enc_pitch}%0A{enc_link}"
    tg_url = f"https://t.me/share/url?url={enc_link}&text={enc_pitch}"

    # --- 3. Premium Button Layout ---
    keyboard = {
        "inline_keyboard": [[
            {"text": "WhatsApp 🟢", "url": wa_url},
            {"text": "Telegram ✈️", "url": tg_url}
        ]]
    }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": final_msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print("✅ Live Update Posted Successfully!")
        else:
            print(f"❌ Telegram API Error: {r.text}")
    except Exception as e:
        print(f"❌ Deployment Error: {e}")

if __name__ == "__main__":
    send_telegram_msg()