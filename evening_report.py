import os
import time
import requests
import yfinance as yf
import telebot
from google import genai
from dotenv import load_dotenv

load_dotenv()

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.nseindia.com/market-data/fii-dii-trading-activity",
    "Connection":      "keep-alive",
    "Sec-Fetch-Dest":  "empty",
    "Sec-Fetch-Mode":  "cors",
    "Sec-Fetch-Site":  "same-origin",
    "Cache-Control":   "no-cache",
    "Pragma":          "no-cache",
}


def _get_nse_session() -> requests.Session:
    """Creates a warmed-up session that NSE's anti-bot layer will accept."""
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(2)
        session.get(
            "https://www.nseindia.com/market-data/fii-dii-trading-activity",
            timeout=15,
        )
        time.sleep(1)
    except Exception as e:
        print(f"NSE session warm-up error: {e}")
    return session


def get_closing_data():
    try:
        nifty = yf.Ticker("^NSEI")
        data = nifty.history(period="5d")
        if data.empty:
            return 0.0, 0.0
        close_val = data["Close"].iloc[-1]
        open_val  = data["Open"].iloc[-1]
        pct_change = ((close_val - open_val) / open_val) * 100
        return close_val, pct_change
    except Exception as e:
        print(f"Nifty fetch error: {e}")
        return 0.0, 0.0


def _parse_amount(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def get_fii_dii_data():
    try:
        session = _get_nse_session()
        resp = session.get(
            "https://www.nseindia.com/api/fiidiiTradeReact",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        print(f"NSE raw response: {data}")

        fii_net = None
        dii_net = None

        for item in data:
            cat = item.get("category", "").strip().upper()

            if "FII" in cat or "FPI" in cat:
                raw = (
                    item.get("buySellNetAmount")
                    or item.get("netAmount")
                    or item.get("net")
                    or item.get("buyAmount", 0)
                )
                fii_net = _parse_amount(raw)

            elif "DII" in cat:
                raw = (
                    item.get("buySellNetAmount")
                    or item.get("netAmount")
                    or item.get("net")
                    or item.get("buyAmount", 0)
                )
                dii_net = _parse_amount(raw)

        if fii_net is not None and dii_net is not None:
            print(f"FII: {fii_net} Cr | DII: {dii_net} Cr")
            return fii_net, dii_net

        print("Could not match FII/DII categories in NSE response.")
        return None, None

    except Exception as e:
        print(f"FII/DII fetch error: {e}")
        return None, None


def get_ai_summary(val: float, pct: float) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set — using fallback summary.")
        return "Market wrapped up the session with notable price action — watch the key levels tomorrow!"

    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            f"Nifty 50 closed at {val:.2f} today ({pct:+.2f}%). "
            "Write exactly ONE sentence summarising the market mood. "
            "Tone: informal, tech-savvy, like a sharp trader. "
            "Do NOT use emojis or hashtags."
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        summary = response.text.strip()
        print(f"AI Summary: {summary}")
        return summary
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "Market wrapped up the session with notable price action — watch the key levels tomorrow!"


def run_evening_report():
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing. Aborting.")
        return

    bot = telebot.TeleBot(token)

    val, pct = get_closing_data()

    fii_net, dii_net = None, None
    for attempt in range(3):
        print(f"Attempt {attempt + 1}/3: Fetching FII/DII data...")
        fii_net, dii_net = get_fii_dii_data()
        if fii_net is not None:
            break
        if attempt < 2:
            print("Retrying in 10 s...")
            time.sleep(10)

    summary = get_ai_summary(val, pct)

    direction = "📈" if pct >= 0 else "📉"
    message = (
        f"☕ *Nivesh Niti: Closing Bell*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{direction} *Nifty 50:* {val:,.2f} ({pct:+.2f}%)\n\n"
    )

    if fii_net is not None and dii_net is not None:
        fii_emoji = "🟢" if fii_net >= 0 else "🔴"
        dii_emoji = "🟢" if dii_net >= 0 else "🔴"
        message += (
            f"🏛️ *Institutional Activity (Net):*\n"
            f"• *FII:* ₹{fii_net:,.2f} Cr {fii_emoji}\n"
            f"• *DII:* ₹{dii_net:,.2f} Cr {dii_emoji}\n\n"
        )
    else:
        message += "⏳ *Institutional Data:* Not yet available from NSE.\n\n"

    message += f"📝 *Day's Take:* {summary}\n\n"
    message += "💎 *Premium:* Whale Watch Excel report coming at 6:45 PM!"

    bot.send_message(chat_id, message, parse_mode="Markdown")
    print("Evening report sent!")


if __name__ == "__main__":
    run_evening_report()
