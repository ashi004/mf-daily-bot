import requests
import os
import json
from dotenv import load_dotenv
from fetcher import generate_smart_report

load_dotenv()

def send_telegram_msg():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Error: Credentials missing.")
        return

    # Generate the Smart Report
    print("📊 Generating Analytics Report...")
    final_msg = generate_smart_report()

    # Dynamic Buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📈 Check Portfolio", "url": "https://www.google.com/finance"},
                {"text": "📢 Share Channel", "url": "https://t.me/share/url?url=https://t.me/NiveshNitiDaily"}
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
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Telegram Report Sent!")
    else:
        print(f"❌ Failed: {response.text}")

if __name__ == "__main__":
    send_telegram_msg()