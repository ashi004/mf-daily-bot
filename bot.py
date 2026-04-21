"""
bot.py
------
Orchestrator called by daily_run.yml.
Retries up to MAX_RETRIES times before giving up.
"""

import os
import time
import telebot
from fetcher import generate_report
from dotenv import load_dotenv

load_dotenv()

MAX_RETRIES = 10
RETRY_DELAY = 60   # seconds


def run_live_bot():
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        print("❌ TELEGRAM_TOKEN missing. Aborting.")
        return
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID missing. Aborting.")
        return

    bot = telebot.TeleBot(token)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🚀 Attempt {attempt}/{MAX_RETRIES}: Generating report…")
            report = generate_report()

            if "Intelligence" in report:
                bot.send_message(chat_id, report, parse_mode="Markdown")
                print("✅ Live report sent!")
                return

            if "Holiday" in report:
                bot.send_message(chat_id, report, parse_mode="Markdown")
                print("🏖️ Holiday message sent.")
                return

            # Unexpected content — treat as a soft error and retry
            print(f"⚠️  Unexpected report content. Retrying in {RETRY_DELAY}s…")

        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")

        if attempt < MAX_RETRIES:
            print(f"🔄 Waiting {RETRY_DELAY}s before retry…")
            time.sleep(RETRY_DELAY)

    # All retries exhausted
    print("🛑 All retries exhausted. Sending failure alert.")
    try:
        admin_id = os.getenv("ADMIN_CHAT_ID") or chat_id
        bot.send_message(
            admin_id,
            "⚠️ *Nivesh Niti Bot:* Failed to fetch market data after 10 attempts. Please check GitHub Actions logs.",
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Failed to send admin alert: {e}")


if __name__ == "__main__":
    run_live_bot()
