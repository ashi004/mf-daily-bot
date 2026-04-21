import os
import yfinance as yf
import telebot
from google import genai
from dotenv import load_dotenv

load_dotenv()


def get_global_markets():
    """Fetches overnight US market data to predict Indian open sentiment."""
    markets = {
        "S&P 500": "^GSPC",
        "Nasdaq":  "^IXIC",
        "Dow Jones": "^DJI",
        "Gift Nifty": "NIFTY50.NS",   # proxy; actual Gift Nifty needs broker API
    }
    results = {}
    for name, ticker in markets.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            if data.empty:
                raise ValueError("Empty data")
            close_val  = data["Close"].iloc[-1]
            open_val   = data["Open"].iloc[-1]
            pct_change = ((close_val - open_val) / open_val) * 100
            results[name] = {"value": close_val, "change": pct_change}
        except Exception as e:
            print(f"Error fetching {name} ({ticker}): {e}")
            results[name] = {"value": 0.0, "change": 0.0}
    return results


def get_ai_strategy(sp500_chg: float, nasdaq_chg: float) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set — using fallback strategy.")
        return "Global cues are mixed — wait for the first 15-minute range to break before entering any trade today."

    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            f"Overnight US Markets: S&P 500 changed {sp500_chg:+.2f}%, "
            f"Nasdaq changed {nasdaq_chg:+.2f}%. "
            "Write exactly ONE sentence of pre-market strategy for Indian equity traders. "
            "Mention gap-up/gap-down prediction and what to watch. "
            "Tone: alert, tech-savvy, like a professional trader. "
            "Do NOT use emojis or hashtags."
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        strategy = response.text.strip()
        print(f"AI Strategy: {strategy}")
        return strategy
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "Global cues are mixed — wait for the first 15-minute range to break before entering any trade today."


def run_morning_report():
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing. Aborting.")
        return

    bot = telebot.TeleBot(token)

    global_data = get_global_markets()

    sp500_val  = global_data.get("S&P 500",   {}).get("value",  0.0)
    sp500_chg  = global_data.get("S&P 500",   {}).get("change", 0.0)
    nasdaq_val = global_data.get("Nasdaq",    {}).get("value",  0.0)
    nasdaq_chg = global_data.get("Nasdaq",    {}).get("change", 0.0)
    dow_val    = global_data.get("Dow Jones", {}).get("value",  0.0)
    dow_chg    = global_data.get("Dow Jones", {}).get("change", 0.0)

    strategy = get_ai_strategy(sp500_chg, nasdaq_chg)

    # Telegram MarkdownV1 uses *text* for bold
    sp_emoji  = "📈" if sp500_chg  >= 0 else "📉"
    nq_emoji  = "📈" if nasdaq_chg >= 0 else "📉"
    dow_emoji = "📈" if dow_chg    >= 0 else "📉"

    message = (
        f"☀️ *Nivesh Niti: Opening Pulse*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌍 *Global Cues (Overnight):*\n"
        f"• *S&P 500:* {sp500_val:,.2f} ({sp500_chg:+.2f}%) {sp_emoji}\n"
        f"• *Nasdaq:* {nasdaq_val:,.2f} ({nasdaq_chg:+.2f}%) {nq_emoji}\n"
        f"• *Dow Jones:* {dow_val:,.2f} ({dow_chg:+.2f}%) {dow_emoji}\n\n"
        f"🎯 *Pre-Market Strategy:*\n"
        f"{strategy}\n\n"
        f"🔔 *Note:* Stay disciplined — wait for the market to settle in the first 15 min!"
    )

    bot.send_message(chat_id, message, parse_mode="Markdown")
    print("Morning report sent!")


if __name__ == "__main__":
    run_morning_report()
