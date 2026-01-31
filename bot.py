import requests
import os
import json
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from fetcher import generate_report

load_dotenv()

# --- ⚠️ SAFETY SWITCH ⚠️ ---
# Set False to go LIVE
TEST_MODE = True

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

    # --- 2. THE FIX: Standard Encoding ---
    
    # The Link (With the + sign)
    invite_link = "https://t.me/+wjibPaNXP-xjZTE1"
    
    # The Text
    invite_pitch = (
        "🚀 *Start tracking your Wealth!* \n\n"
        "Get daily Nifty updates, Mutual Fund tracking, and Gold rates automatically on Telegram.\n\n"
        "👇 *Join Nivesh Niti here (It's Free):*"
    )
    
    # ENCODING LOGIC:
    # We use quote() which turns '+' into '%2B' automatically.
    # WhatsApp decodes '%2B' back to '+' (Correct).
    # Telegram server receives '%2B' and understands it is a '+' (Correct).
    
    encoded_pitch = urllib.parse.quote(invite_pitch)
    encoded_link = urllib.parse.quote(invite_link)

    # WhatsApp URL: We combine Pitch + NewLine + Link into the 'text' parameter
    wa_url = f"https://api.whatsapp.com/send?text={encoded_pitch}%0A{encoded_link}"
    
    # Telegram URL: We separate 'url' and 'text' parameters correctly
    # Note: We must encode the 'url' parameter itself so the '+' survives
    tg_url = f"https://t.me/share/url?url={encoded_link}&text={encoded_pitch}"

    # --- 3. Button Layout ---
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "WhatsApp 🟢", "url": wa_url},
                {"text": "Telegram ✈️", "url": tg_url}
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