import os
import time
import yfinance as yf
import telebot
from dotenv import load_dotenv

load_dotenv()

# ─── GLOBAL MARKETS ──────────────────────────────────────────────────────────

MARKETS = {
    "S&P 500": "^GSPC",
    "Nasdaq":  "^IXIC",
    "Dow Jones": "^DJI",
    "SGX Nifty": "^NSEI",   # proxy for Nifty futures sentiment
}

def get_global_markets() -> dict:
    """
    Fetch overnight US market data.
    Returns a dict: { name: {"value": float, "change": float} }
    """
    results = {}
    for name, ticker in MARKETS.items():
        for attempt in range(3):
            try:
                data = yf.Ticker(ticker).history(period="2d")
                if data.empty:
                    raise ValueError("Empty dataframe")
                close_val  = data["Close"].iloc[-1]
                open_val   = data["Open"].iloc[-1]
                pct_change = ((close_val - open_val) / open_val) * 100
                results[name] = {
                    "value":  round(close_val, 2),
                    "change": round(pct_change, 2),
                }
                break
            except Exception as e:
                print(f"[{name}] Attempt {attempt+1} failed: {e}")
                time.sleep(4)
        else:
            results[name] = {"value": 0.0, "change": 0.0}

    return results

# ─── AI STRATEGY ─────────────────────────────────────────────────────────────

def get_ai_strategy(sp500_chg: float, nasdaq_chg: float) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("[AI] GEMINI_API_KEY not set – using fallback strategy.")
        return _fallback_strategy(sp500_chg, nasdaq_chg)

    prompt = (
        f"Overnight US markets: S&P 500 {sp500_chg:+.2f}%, Nasdaq {nasdaq_chg:+.2f}%. "
        "Write exactly ONE sentence morning strategy for Indian stock market traders "
        "predicting gap-up or gap-down opening. Tone: alert, tech-savvy, no emojis."
    )

    for model in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.0-pro"):
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model=model, contents=prompt)
            text = response.text.strip()
            if text:
                print(f"[AI] Strategy from {model}: {text}")
                return text
        except Exception as e:
            print(f"[AI] {model} failed: {e}")

    return _fallback_strategy(sp500_chg, nasdaq_chg)

def _fallback_strategy(sp500_chg: float, nasdaq_chg: float) -> str:
    avg = (sp500_chg + nasdaq_chg) / 2
    if avg > 0.5:
        return "Strong positive global cues point to a gap-up — wait for the first 15-min candle to confirm before entering."
    elif avg < -0.5:
        return "Weak global cues suggest a gap-down — avoid panic selling and watch key support before entering any trade."
    else:
        return "Mixed global cues — market may open flat; wait for the opening range before taking a directional bet."

# ─── MAIN REPORT ─────────────────────────────────────────────────────────────

def run_morning_report():
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing – aborting.")
        return

    bot = telebot.TeleBot(token)

    # 1. Global market data
    global_data = get_global_markets()

    sp500   = global_data.get("S&P 500",   {"value": 0.0, "change": 0.0})
    nasdaq  = global_data.get("Nasdaq",    {"value": 0.0, "change": 0.0})
    dow     = global_data.get("Dow Jones", {"value": 0.0, "change": 0.0})

    sp500_chg  = sp500["change"]
    nasdaq_chg = nasdaq["change"]

    def arrow(chg): return "🟢" if chg >= 0 else "🔴"

    # 2. AI strategy
    strategy = get_ai_strategy(sp500_chg, nasdaq_chg)

    # 3. Build message
    message = (
        f"☀️ *Nivesh Niti: Opening Pulse*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌍 *Global Cues (Overnight):*\n"
        f"• S&P 500:  `{sp500['value']:,.2f}` ({sp500_chg:+.2f}%) {arrow(sp500_chg)}\n"
        f"• Nasdaq:   `{nasdaq['value']:,.2f}` ({nasdaq_chg:+.2f}%) {arrow(nasdaq_chg)}\n"
        f"• Dow Jones: `{dow['value']:,.2f}` ({dow['change']:+.2f}%) {arrow(dow['change'])}\n\n"
        f"🎯 *Pre-Market Strategy:*\n"
        f"{strategy}\n\n"
        f"🔔 *Tip:* First 15 minutes are noise — let the market show its hand!"
    )

    bot.send_message(chat_id, message, parse_mode="Markdown")
    print("✅ Morning report sent.")

if __name__ == "__main__":
    run_morning_report()
