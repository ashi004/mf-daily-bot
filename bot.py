import requests
import os
from dotenv import load_dotenv
from fetcher import get_latest_nav

# Load environment variables
load_dotenv()

def send_telegram_msg(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Error: Missing Telegram Token or Chat ID.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"  # Allows bolding text with *stars*
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram Message Sent Successfully!")
        else:
            print(f"❌ Error Sending Message: {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Nivesh Niti Bot...")
    
    # 1. Fetch Data
    msg = get_latest_nav()
    
    # 2. Add a Header for Telegram
    # We add a bold title using Markdown
    final_msg = f"*🇮🇳 Nivesh Niti Daily Update*\n\n{msg}\n\n_Disclaimer: For educational purposes only._"
    
    # 3. Send
    send_telegram_msg(final_msg)