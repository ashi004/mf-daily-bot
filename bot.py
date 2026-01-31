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

    # 1. Generate the Report
    day_index = datetime.today().weekday()
    if day_index >= 5:
        final_msg = generate_report(report_type="weekly")
    else:
        final_msg = generate_report(report_type="daily")

    # ==========================================
    # STRATEGY 1: "SHARE THE UPDATE" LINKS
    # (User shares the specific daily report)
    # ==========================================
    update_caption = "📉 Check out today's Market & Mutual Fund Update by Nivesh Niti!"
    
    # We use the public channel link for the update source
    channel_link = "https://t.me/NiveshNitiDaily"
    
    # Encode for URL safety
    enc_update_text = urllib.parse.quote(update_caption)
    enc_channel_link = urllib.parse.quote(channel_link)

    # Links
    wa_share_update = f"https://api.whatsapp.com/send?text={enc_update_text}%0A%0A{enc_channel_link}"
    tg_share_update = f"https://t.me/share/url?url={channel_link}&text={enc_update_text}"

    # ==========================================
    # STRATEGY 2: "INVITE FRIENDS" LINKS
    # (User shares the Channel Invite + Pitch)
    # ==========================================
    invite_link = "https://t.me/+wjibPaNXP-xjZTE1" # Your specific invite link
    invite_pitch = (
        "🚀 *Master the Market with Nivesh Niti!*\n\n"
        "Get daily automated Mutual Fund tracking, Nifty updates, and Gold rates directly on Telegram.\n\n"
        "✅ Daily NAV Alerts\n"
        "✅ Weekly Winners & Losers\n"
        "✅ 100% Free & Automated\n\n"
        "👇 *Join smart investors here:*"
    )
    
    enc_invite_pitch = urllib.parse.quote(invite_pitch)
    enc_invite_link = urllib.parse.quote(invite_link)

    # Links
    wa_invite = f"https://api.whatsapp.com/send?text={enc_invite_pitch}%0A{enc_invite_link}"
    tg_invite = f"https://t.me/share/url?url={invite_link}&text={enc_invite_pitch}"

    # ==========================================
    # BUTTON LAYOUT
    # ==========================================
    keyboard = {
        "inline_keyboard": [
            # Section 1: Share the News (Actionable)
            [
                {"text": "📤 Share this Update (WhatsApp)", "url": wa_share_update}
            ],
            [
                {"text": "✈️ Forward to Telegram Friends", "url": tg_share_update}
            ],
            # Section 2: Grow the Channel (Strategic)
            [
                {"text": "------------------------------------------------", "callback_data": "dummy"}
            ],
            [
                {"text": "🚀 Invite Friends to Join Channel", "url": wa_invite}
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