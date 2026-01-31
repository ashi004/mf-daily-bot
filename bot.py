import requests
import os
import json
from datetime import datetime
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

    # --- 1. Create the Interactive Buttons ---
    # This 'reply_markup' creates buttons below the message
    keyboard = {
        "inline_keyboard": [
            [
                # BUTTON 1: The Money Button 
                # (Later, you will replace the 'url' with your Zerodha/INDmoney referral link)
                {"text": "🚀 Invest in this Fund", "url": "https://www.google.com/search?q=Axis+Bluechip+Fund+Growth+Direct+Plan"}
            ],
            [
                # BUTTON 2: The Growth Button
                # (This helps people share your channel)
                {"text": "📢 Share Nivesh Niti", "url": "https://t.me/share/url?url=https://t.me/NiveshNitiDaily"}
            ]
        ]
    }

    # --- 2. Format the Message ---
    # Get today's date in a nice format (e.g., "30 Jan 2026")
    today_date = datetime.now().strftime("%d %b %Y")
    
    # Construct the final message with Markdown
    # *Bold Text* and _Italics_
    final_msg = (
        f"📅 *Daily Update: {today_date}*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{message}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Consistency is the key to wealth._"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": final_msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)  # Attach the buttons
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
    
    # Fetch Data
    msg = get_latest_nav()
    
    # Send with new formatting
    send_telegram_msg(msg)