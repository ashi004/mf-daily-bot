import requests
import os
import json
import urllib.parse # We need this to format the text for links
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

    # --- 2. Create Smart Share Links ---
    # The text people will see when they share
    share_text = "Get daily Market & Mutual Fund updates automatically on Telegram! 🚀"
    share_link = "https://t.me/NiveshNitiDaily"
    
    # We must "encode" the text so URLs don't break (spaces become %20)
    encoded_text = urllib.parse.quote(share_text)
    encoded_link = urllib.parse.quote(share_link)

    # WhatsApp Link
    wa_url = f"https://api.whatsapp.com/send?text={encoded_text}%20{encoded_link}"
    
    # Telegram Link
    tg_url = f"https://t.me/share/url?url={share_link}&text={encoded_text}"
    
    # LinkedIn Link (Great for your educated audience)
    li_url = f"https://www.linkedin.com/sharing/share-offsite/?url={share_link}"

    # --- 3. Multi-Row Button Layout ---
    keyboard = {
        "inline_keyboard": [
            [
                # Row 1: The Giants
                {"text": "Share on WhatsApp 🟢", "url": wa_url}
            ],
            [
                # Row 2: Professional & Internal
                {"text": "Share on LinkedIn 💼", "url": li_url},
                {"text": "Forward on Telegram ✈️", "url": tg_url}
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