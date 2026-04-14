import os
import time
import telebot
from fetcher import generate_report

# Optional: If you ever run this locally on your machine, this loads the .env file
from dotenv import load_dotenv
load_dotenv()

# --- SAFETY CHECK: API KEYS ---
if not os.getenv("TELEGRAM_TOKEN") or not os.getenv("GEMINI_API_KEY"):
    print("⚠️ WARNING: Missing API Keys in Environment! The bot might fail.")

# --- RETRY CONFIGURATION ---
MAX_RETRIES = 10  # Try up to 10 times
RETRY_DELAY = 60  # Wait 60 seconds between attempts (1 minute)

def run_live_bot():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Cannot start bot: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return

    bot = telebot.TeleBot(token)
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"🚀 Attempt {attempt + 1}: Generating Report...")
            report = generate_report()
            
            # CRITICAL: Only send if we got real values, not a holiday/error msg
            if "Intelligence" in report:
                bot.send_message(chat_id, report, parse_mode="Markdown")
                print("✅ Successfully sent Live Report!")
                return # Exit the loop and end the script
            
            elif "Holiday" in report:
                bot.send_message(chat_id, report, parse_mode="Markdown")
                print("☕ Holiday Message Sent.")
                return
                
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"🔄 Waiting {RETRY_DELAY}s before retrying...")
                time.sleep(RETRY_DELAY)
            else:
                print("🛑 All retries exhausted. Sending error alert to Admin.")
                # Optional: bot.send_message(MY_PERSONAL_ID, "Bot failed to fetch data after 10 tries.")

if __name__ == "__main__":
    run_live_bot()