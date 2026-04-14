import os
import yfinance as yf
import telebot
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_market_data():
    # GIFT Nifty proxy via yfinance (^NSEI is the standard Nifty 50 Index)
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="2d")
    
    current_val = hist['Close'].iloc[-1]
    prev_val = hist['Close'].iloc[-2]
    change = current_val - prev_val
    pct_change = (change / prev_val) * 100
    
    return current_val, pct_change

def run_morning_report():
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    val, pct = get_market_data()
    sentiment = "Bullish 📈" if pct > 0 else "Bearish 📉"
    
    prompt = f"The Nifty 50 pre-open settled at {val:.2f} ({pct:+.2f}%). Give a 1-sentence opening strategy for retail traders. Tone: Helpful friend."
    ai_advice = client.models.generate_content(model="gemini-1.5-flash", contents=prompt).text.strip()

    message = (
        f"☀️ *Nivesh Niti: Morning Pulse*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌏 *GIFT Nifty/Pre-Open:* {val:.2f}\n"
        f"📊 *Bias:* {sentiment} ({pct:+.2f}%)\n\n"
        f"💡 *Opening Insight:* _{ai_advice}_\n\n"
        f"🚀 Market opens in 5 minutes. Stay disciplined!"
    )
    
    bot.send_message(chat_id, message, parse_mode="Markdown")

if __name__ == "__main__":
    run_morning_report()