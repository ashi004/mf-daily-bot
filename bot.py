import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from fetcher import generate_report

load_dotenv()

# --- ⚠️ SAFETY SWITCH ⚠️ ---
# Set True for Testing, False for Real Audience
TEST_MODE = True 

def send_telegram_msg():
    token = os.getenv("TELEGRAM_TOKEN")
    
    # Logic: Switch Channels based on Mode
    if TEST_MODE:
        print(f"🚧 TEST MODE ON: Sending to Test Lab (-1003461082219)")
        chat_id = os.getenv("TEST_CHANNEL_ID") 
    else:
        print("🔴 LIVE MODE: Sending to Public Audience")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Error: Missing Token or Channel ID (Check GitHub Secrets)")
        return

    # --- Day Check ---
    day_index = datetime.today().weekday()
    is_weekend = day_index >= 5
    
    if is_weekend:
        print("Generating WEEKLY Report...")
        final_msg = generate_report(report_type="weekly")
    else:
        print("Generating DAILY Report...")
        final_msg = generate_report(report_type="daily")

    # --- Button Strategy ---
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📢 Share Nivesh Niti", "url": "https://t.me/share/url?url=https://t.me/NiveshNitiDaily"}
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
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Message Sent!")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    send_telegram_msg()