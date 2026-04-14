import os
import time
import yfinance as yf
import telebot
from google import genai
from nselib import capital_market
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
    """Fetches FII & DII net activity using a safer nselib check."""
    try:
        # Safely check if the method exists in this version of the library
        if hasattr(capital_market, 'fii_dii_trading_activity'):
            df = capital_market.fii_dii_trading_activity()
        else:
            print("⚠️ FII/DII method missing in this version of nselib.")
            return None, None
            
        if df is None or df.empty:
            return None, None
            
        df.columns = [str(c).lower().replace(' ', '_') for c in df.columns]
        net_col = [c for c in df.columns if 'net' in c][0]
        cat_col = [c for c in df.columns if 'category' in c][0]

        fii_net = float(df[df[cat_col].str.contains('FII', na=False, case=False)][net_col].values[0])
        dii_net = float(df[df[cat_col].str.contains('DII', na=False, case=False)][net_col].values[0])
        
        return fii_net, dii_net
    except Exception as e:
        print(f"⚠️ NSE Data Error: {e}")
        return None, None

def run_evening_report():
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    val, pct = get_closing_data()
    
    # Quick retry loop for FII/DII (waits 5 seconds, not 5 minutes, for fast testing)
    fii_net, dii_net = None, None
    for attempt in range(2): 
        print(f"Attempt {attempt + 1}: Fetching FII/DII data...")
        fii_net, dii_net = get_fii_dii_data()
        if fii_net is not None: 
            break
        time.sleep(5)
    
    # Generating AI Summary with the correct model string
    try:
        prompt = f"Nifty closed at {val:.2f} today ({pct:+.2f}%). Write a 1-sentence market mood summary. Informal/Tech-savvy."
        # Using gemini-2.0-flash to fix the 404 error
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