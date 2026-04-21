import os
import time
import requests
import yfinance as yf
import telebot
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_closing_data():
    try:
        nifty = yf.Ticker("^NSEI")
        data = nifty.history(period="1d")
        close_val = data['Close'].iloc[-1]
        open_val = data['Open'].iloc[-1]
        pct_change = ((close_val - open_val) / open_val) * 100
        return close_val, pct_change
    except Exception:
        return 0.0, 0.0

def get_fii_dii_data():
    """Stealth fetcher that bypasses nselib and acts like a real browser."""
    try:
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        # Create a session to hold the security cookies
        session = requests.Session()
        
        # 1. Visit homepage first to get the required cookies
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        # 2. Fetch the actual FII/DII JSON data
        response = session.get(url, headers=headers, timeout=10)
        data = response.json()
        
        fii_net = None
        dii_net = None
        
        for item in data:
            cat = item.get('category', '').upper()
            if cat.startswith('FII'):
                fii_net = float(item.get('buySellNetAmount', 0))
            elif cat.startswith('DII'):
                dii_net = float(item.get('buySellNetAmount', 0))
                
        if fii_net is not None and dii_net is not None:
            return fii_net, dii_net
        return None, None
        
    except Exception as e:
        print(f"⚠️ Direct NSE Fetch Error: {e}")
        return None, None

def run_evening_report():
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    val, pct = get_closing_data()
    
    # Retry loop for FII/DII
    fii_net, dii_net = None, None
    for attempt in range(3): 
        print(f"Attempt {attempt + 1}: Fetching FII/DII stealth data...")
        fii_net, dii_net = get_fii_dii_data()
        if fii_net is not None: 
            break
        time.sleep(5)
    
    # Generating AI Summary
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        prompt = f"Nifty closed at {val:.2f} today ({pct:+.2f}%). Write a 1-sentence market mood summary. Informal/Tech-savvy."
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        summary = response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        summary = "Market ended the day with interesting price action. Watch the levels tomorrow!"

    message = (
        f"☕ *Nivesh Niti: Closing Bell*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏁 *Nifty 50:* {val:.2f} ({pct:+.2f}%)\n\n"
    )

    if fii_net is not None:
        fii_emoji = "🟢" if fii_net > 0 else "🔴"
        dii_emoji = "🟢" if dii_net > 0 else "🔴"
        message += (
            f"🏛️ *Institutional Activity (Net):*\n"
            f"• **FII:** ₹{fii_net:,.2f} Cr {fii_emoji}\n"
            f"• **DII:** ₹{dii_net:,.2f} Cr {dii_emoji}\n\n"
        )
    else:
        message += "⏳ *Institutional Data:* Data not available yet from NSE.\n\n"

    message += f"📝 *Day's Take:* {summary}\n\n"
    message += "💎 *Premium:* Whale Watch Excel report coming at 6:45 PM!"
    
    bot.send_message(chat_id, message, parse_mode="Markdown")

if __name__ == "__main__":
    run_evening_report()