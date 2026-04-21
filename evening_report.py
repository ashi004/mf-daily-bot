import os
import time
import requests
import yfinance as yf
import telebot
from dotenv import load_dotenv

load_dotenv()

# ─── NIFTY DATA ──────────────────────────────────────────────────────────────

def get_closing_data():
    """Fetch Nifty 50 closing price and % change."""
    for attempt in range(3):
        try:
            nifty = yf.Ticker("^NSEI")
            data = nifty.history(period="2d")   # 2d to ensure we get today's bar
            if data.empty:
                raise ValueError("Empty data returned")
            close_val = data['Close'].iloc[-1]
            open_val  = data['Open'].iloc[-1]
            pct_change = ((close_val - open_val) / open_val) * 100
            return round(close_val, 2), round(pct_change, 2)
        except Exception as e:
            print(f"[Nifty] Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    return 0.0, 0.0

# ─── FII / DII ────────────────────────────────────────────────────────────────

def _build_nse_session():
    """Create a requests Session that mimics a real browser visiting NSE."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
    }
    session = requests.Session()
    session.headers.update(headers)

    # Step 1 – load homepage to collect initial cookies
    try:
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(2)
    except Exception as e:
        print(f"[NSE Session] Homepage visit failed: {e}")

    # Step 2 – visit the FII/DII page so NSE knows the referrer
    try:
        session.get(
            "https://www.nseindia.com/market-data/fii-dii-activity",
            timeout=15
        )
        time.sleep(2)
    except Exception as e:
        print(f"[NSE Session] FII page visit failed: {e}")

    return session

def _parse_net_value(item: dict) -> float | None:
    """
    NSE has changed field names over time.
    Try every known variant and strip commas/spaces before converting.
    """
    for key in ("netValue", "buySellNetAmount", "net", "NET"):
        raw = item.get(key)
        if raw is not None:
            try:
                return float(str(raw).replace(",", "").strip())
            except ValueError:
                pass
    return None

def get_fii_dii_via_nse_api(session: requests.Session):
    """Primary method: call the NSE JSON endpoint directly."""
    api_url = "https://www.nseindia.com/api/fiidiiTradeReact"
    api_headers = {
        "Accept":          "application/json, text/plain, */*",
        "Referer":         "https://www.nseindia.com/market-data/fii-dii-activity",
        "X-Requested-With": "XMLHttpRequest",
    }
    response = session.get(api_url, headers=api_headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    fii_net = dii_net = None
    for item in data:
        cat = item.get("category", "").strip().upper()
        val = _parse_net_value(item)
        if val is None:
            continue
        if "FII" in cat or "FPI" in cat:
            fii_net = val
        elif "DII" in cat:
            dii_net = val

    return fii_net, dii_net

def get_fii_dii_via_nselib():
    """Fallback method: use nselib if installed."""
    try:
        from nselib import capital_market
        df = capital_market.fii_dii_trading_activity()
        if df is None or df.empty:
            return None, None

        fii_net = dii_net = None
        for _, row in df.iterrows():
            cat = str(row.get("Category", "")).strip().upper()
            # nselib column might be 'Net Purchase / Sales'
            net_col = next(
                (c for c in df.columns if "net" in c.lower()),
                None
            )
            if net_col is None:
                continue
            try:
                val = float(str(row[net_col]).replace(",", "").strip())
            except ValueError:
                continue
            if "FII" in cat or "FPI" in cat:
                fii_net = val
            elif "DII" in cat:
                dii_net = val

        return fii_net, dii_net
    except Exception as e:
        print(f"[nselib fallback] Error: {e}")
        return None, None

def get_fii_dii_data():
    """
    Try NSE API first (with a warm-up session), then nselib.
    Returns (fii_net, dii_net) in crores, or (None, None) on total failure.
    """
    session = _build_nse_session()

    for attempt in range(3):
        print(f"[FII/DII] NSE API attempt {attempt + 1}…")
        try:
            fii_net, dii_net = get_fii_dii_via_nse_api(session)
            if fii_net is not None and dii_net is not None:
                print(f"[FII/DII] Got data → FII: {fii_net}, DII: {dii_net}")
                return fii_net, dii_net
            else:
                print("[FII/DII] Parsed OK but values still None – retrying.")
        except Exception as e:
            print(f"[FII/DII] NSE API error: {e}")
        time.sleep(6)

    # Fallback
    print("[FII/DII] Trying nselib fallback…")
    fii_net, dii_net = get_fii_dii_via_nselib()
    if fii_net is not None:
        print(f"[FII/DII] nselib gave data → FII: {fii_net}, DII: {dii_net}")
    return fii_net, dii_net

# ─── AI SUMMARY ───────────────────────────────────────────────────────────────

def get_ai_summary(val: float, pct: float) -> str:
    """Generate a 1-line market mood with Gemini; falls back gracefully."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("[AI] GEMINI_API_KEY not set – using fallback summary.")
        return _fallback_summary(pct)

    prompt = (
        f"Nifty 50 closed at {val:.2f} today ({pct:+.2f}%). "
        "Write exactly ONE sentence summarising the market mood. "
        "Tone: informal, tech-savvy, no emojis."
    )

    for model in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.0-pro"):
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model=model, contents=prompt)
            text = response.text.strip()
            if text:
                print(f"[AI] Summary from {model}: {text}")
                return text
        except Exception as e:
            print(f"[AI] {model} failed: {e}")

    return _fallback_summary(pct)

def _fallback_summary(pct: float) -> str:
    if pct > 0.5:
        return "Bulls held the fort today — momentum looks constructive, watch for follow-through tomorrow."
    elif pct < -0.5:
        return "Bears had the upper hand today — stay cautious and watch key support levels."
    else:
        return "Flat close with indecision — wait for a clear breakout before committing."

# ─── MAIN REPORT ─────────────────────────────────────────────────────────────

def run_evening_report():
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing – aborting.")
        return

    bot = telebot.TeleBot(token)

    # 1. Nifty data
    val, pct = get_closing_data()

    # 2. FII / DII data
    fii_net, dii_net = get_fii_dii_data()

    # 3. AI summary
    summary = get_ai_summary(val, pct)

    # 4. Build message
    arrow = "🟢" if pct >= 0 else "🔴"
    message = (
        f"☕ *Nivesh Niti: Closing Bell*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏁 *Nifty 50:* `{val:.2f}` ({pct:+.2f}%) {arrow}\n\n"
    )

    if fii_net is not None and dii_net is not None:
        fii_emoji = "🟢" if fii_net >= 0 else "🔴"
        dii_emoji = "🟢" if dii_net >= 0 else "🔴"
        message += (
            f"🏛️ *Institutional Activity (Net Cr):*\n"
            f"• FII: ₹{fii_net:,.2f} Cr {fii_emoji}\n"
            f"• DII: ₹{dii_net:,.2f} Cr {dii_emoji}\n\n"
        )
    else:
        message += (
            "⏳ *Institutional Data:* NSE hasn't published today's data yet.\n\n"
        )

    message += f"📝 *Day's Take:* {summary}\n\n"
    message += "💎 *Premium:* Whale Watch Excel report coming at 6:45 PM!"

    bot.send_message(chat_id, message, parse_mode="Markdown")
    print("✅ Evening report sent.")

if __name__ == "__main__":
    run_evening_report()
