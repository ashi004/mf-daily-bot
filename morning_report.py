import os
import yfinance as yf
import telebot
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_global_markets():
    """Fetches US market closes to predict Indian market sentiment."""
    # Using S&P 500 and Nasdaq as they are highly reliable on yfinance
    markets = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC"}
    results = {}
    for name, ticker in markets.items():
        try:
            data = yf.Ticker(ticker).history(period="1d")
            close_val = data['Close'].iloc[-1]
            open_val = data['Open'].iloc[-1]
            pct_change = ((close_val - open_val) / open_val) * 100
            results[name] = {"value": close_val, "change": pct_change}
        except Exception as e:
            print(f"⚠️ Error fetching {name}: {e}")
            results[name] = {"value": 0.0, "change": 0.0}
    return results

def run_morning_report():
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    global_data = get_global_markets()
    
    sp500_chg = global_data.get("S&P 500", {}).get("change", 0)
    nasdaq_chg = global_data.get("Nasdaq", {}).get("change", 0)
    
    # Generate AI Strategy based on Global Cues
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        prompt = f"US Markets closed overnight: S&P 500 changed {sp500_chg:+.2f}%, Nasdaq changed {nasdaq_chg:+.2f}%. Write a 1-sentence morning strategy for Indian stock market traders predicting the gap up or gap down. Tone: Alert and tech-savvy."
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        summary = response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        summary = "Global cues are mixed. Watch for the first 15-minute range breakout before taking a position today."

    message = (
        f"☀️ *Nivesh Niti: Opening Pulse*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌍 *Global Cues (Overnight):*\n"
        f"• **S&P 500:** {global_data['S&P 500']['value']:.2f} ({sp500_chg:+.2f}%)\n"
        f"• **Nasdaq:** {global_data['Nasdaq']['value']:.2f} ({nasdaq_chg:+.2f}%)\n\n"
        f"🎯 *Pre-Market Strategy:*\n"
        f"{summary}\n\n"
        f"🔔 *Note:* Stay disciplined and wait for the market to settle!"
    )
    
    bot.send_message(chat_id, message, parse_mode="Markdown")

if __name__ == "__main__":
    run_morning_report()