import os
import time
import yfinance as yf
import telebot
import pandas as pd
from google import genai
from nselib import capital_market
from dotenv import load_dotenv

load_dotenv()

def get_closing_data():
    nifty = yf.Ticker("^NSEI")
    data = nifty.history(period="1d")
    close_val = data['Close'].iloc[-1]
    open_val = data['Open'].iloc[-1]
    pct_change = ((close_val - open_val) / open_val) * 100
    return close_val, pct_change

def get_fii_dii_data():
    """Fetches FII & DII net activity for the day."""
    try:
        df = capital_market.fii_dii_trading_activity()
        if df is None or df.empty:
            return None, None
            
        df.columns = [str(c).lower().replace(' ', '_') for c in df.columns]
        net_col = [c for c in df.columns if 'net' in c][0]
        cat_col = [c for c in df.columns if 'category' in c][0]

        fii_net = float(df[df[cat_col].str.contains('FII', na=False, case=False)][net_col].values[0])
        dii_net = float(df[df[cat_col].str.contains('DII', na=False, case=False)][net_col].values[0])
        
        return fii_net, dii_net
    except Exception as e:
        print(f"⚠️ Fetch Error or Data Not Ready: {e}")
        return None, None

def run_evening_report():
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # 1. Get Market Prices
    val, pct = get_closing_data()
    
    # 2. SMART RETRY LOGIC FOR FII/DII
    fii_net, dii_net = None, None
    max_retries = 2 # Will try at 6:30, then 6:35, then 6:40
    wait_seconds = 300 # 5 minutes
    
    for attempt in range(max_retries + 1):
        print(f"Attempt {attempt + 1}: Fetching FII/DII data...")
        fii_net, dii_net = get_fii_dii_data()
        
        if fii_net is not None and dii_net is not None:
            print("✅ FII/DII Data found!")
            break # Exit the loop, we have the data!
            
        if attempt < max_retries:
            print(f"⏳ Data not published yet. Waiting {wait_seconds//60} minutes...")
            time.sleep(wait_seconds) # Pause script for 5 minutes
    
    # 3. Generate AI Summary
    prompt = f"Nifty closed at {val:.2f} today, a change of {pct:+.2f}%. Write a 2-sentence summary of the market mood. Tone: Tech-savvy and informal."
    summary = client.models.generate_content(model="gemini-1.5-flash", contents=prompt).text.strip()

    # 4. Construct the Message
    message = (
        f"☕ *Nivesh Niti: Closing Bell*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏁 *Nifty 50:* {val:.2f} ({pct:+.2f}%)\n\n"
    )

    if fii_net is not None and dii_net is not None:
        fii_emoji = "🟢" if fii_net > 0 else "🔴"
        dii_emoji = "🟢" if dii_net > 0 else "🔴"
        
        message += (
            f"🏛️ *Institutional Activity (Net):*\n"
            f"• **FII:** ₹{fii_net:,.2f} Cr {fii_emoji}\n"
            f"• **DII:** ₹{dii_net:,.2f} Cr {dii_emoji}\n\n"
        )
    else:
        message += "⏳ *Institutional Data:* NSE hasn't published today's FII/DII figures even after retries.\n\n"

    message += (
        f"📝 *Day's Take:* {summary}\n\n"
        f"💎 *Premium Members:* The Whale Watch report drops at 6:45 PM in Alpha Insights!"
    )
    
    bot.send_message(chat_id, message, parse_mode="Markdown")

if __name__ == "__main__":
    run_evening_report()