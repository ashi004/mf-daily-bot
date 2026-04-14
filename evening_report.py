import os
import yfinance as yf
import telebot
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_closing_data():
    # Fetching Nifty 50 for the day's close
    nifty = yf.Ticker("^NSEI")
    data = nifty.history(period="1d")
    close_val = data['Close'].iloc[-1]
    open_val = data['Open'].iloc[-1]
    pct_change = ((close_val - open_val) / open_val) * 100
    return close_val, pct_change

def run_evening_report():
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    val, pct = get_closing_data()
    
    prompt = f"Nifty closed at {val:.2f} today, a change of {pct:+.2f}%. Write a 2-sentence summary of the market mood. Tone: Tech-savvy and informal."
    summary = client.models.generate_content(model="gemini-1.5-flash", contents=prompt).text.strip()

    message = (
        f"☕ *Nivesh Niti: Closing Bell*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏁 *Nifty 50:* {val:.2f} ({pct:+.2f}%)\n\n"
        f"📝 *Day's Take:* {summary}\n\n"
        f"💎 *Premium Members:* Check 'Alpha Insights' for the Whale Watch report coming at 6:45 PM!"
    )
    
    bot.send_message(chat_id, message, parse_mode="Markdown")

if __name__ == "__main__":
    run_evening_report()