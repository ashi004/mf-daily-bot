"""
fetcher.py
----------
Core data-fetching + report-generation module used by bot.py.
Returns a Telegram-formatted markdown string.
"""

import os
import time
import requests
import yfinance as yf
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ─── NSE SESSION ──────────────────────────────────────────────────────────────

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
    "Sec-Fetch-Dest":  "empty",
    "Sec-Fetch-Mode":  "cors",
    "Sec-Fetch-Site":  "same-origin",
    "Cache-Control":   "no-cache",
}

NSE_HOLIDAYS_2025_2026 = {
    # 2025
    "2025-01-26", "2025-02-19", "2025-03-14",
    "2025-03-31", "2025-04-10", "2025-04-14",
    "2025-04-18", "2025-05-01", "2025-08-15",
    "2025-08-27", "2025-10-02", "2025-10-02",
    "2025-10-20", "2025-10-24", "2025-11-05",
    "2025-12-25",
    # 2026
    "2026-01-26", "2026-03-20", "2026-04-03",
    "2026-04-06", "2026-04-14", "2026-05-01",
    "2026-08-15", "2026-10-02", "2026-10-29",
    "2026-11-11", "2026-12-25",
}


def is_market_holiday() -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    return today in NSE_HOLIDAYS_2025_2026


def _get_nse_session() -> requests.Session:
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
        print(f"NSE warm-up error: {e}")
    return session


# ─── INDIVIDUAL FETCHERS ───────────────────────────────────────────────────────

def _parse_amount(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def fetch_nifty():
    try:
        data = yf.Ticker("^NSEI").history(period="5d")
        if data.empty:
            return 0.0, 0.0
        close_val  = data["Close"].iloc[-1]
        open_val   = data["Open"].iloc[-1]
        pct_change = ((close_val - open_val) / open_val) * 100
        return close_val, pct_change
    except Exception as e:
        print(f"Nifty fetch error: {e}")
        return 0.0, 0.0


def fetch_fii_dii():
    try:
        session = _get_nse_session()
        resp = session.get(
            "https://www.nseindia.com/api/fiidiiTradeReact",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"NSE FII/DII raw: {data}")

        fii_net = None
        dii_net = None

        for item in data:
            cat = item.get("category", "").strip().upper()
            if "FII" in cat or "FPI" in cat:
                raw = (
                    item.get("buySellNetAmount")
                    or item.get("netAmount")
                    or item.get("net")
                    or 0
                )
                fii_net = _parse_amount(raw)
            elif "DII" in cat:
                raw = (
                    item.get("buySellNetAmount")
                    or item.get("netAmount")
                    or item.get("net")
                    or 0
                )
                dii_net = _parse_amount(raw)

        if fii_net is not None and dii_net is not None:
            return fii_net, dii_net
        return None, None

    except Exception as e:
        print(f"FII/DII fetch error: {e}")
        return None, None


def fetch_global_markets():
    tickers = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow Jones": "^DJI"}
    results = {}
    for name, sym in tickers.items():
        try:
            data = yf.Ticker(sym).history(period="5d")
            if data.empty:
                raise ValueError("empty")
            c = data["Close"].iloc[-1]
            o = data["Open"].iloc[-1]
            results[name] = {"value": c, "change": ((c - o) / o) * 100}
        except Exception as e:
            print(f"Global market error ({name}): {e}")
            results[name] = {"value": 0.0, "change": 0.0}
    return results


def fetch_market_breadth():
    """Returns advance-decline ratio via a simple NSE endpoint."""
    try:
        session = _get_nse_session()
        resp = session.get(
            "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
            timeout=15,
        )
        data = resp.json()
        advances = data.get("advance", {}).get("advances", "N/A")
        declines = data.get("advance", {}).get("declines", "N/A")
        unchanged = data.get("advance", {}).get("unchanged", "N/A")
        return advances, declines, unchanged
    except Exception as e:
        print(f"Breadth fetch error: {e}")
        return "N/A", "N/A", "N/A"


# ─── AI SUMMARY ───────────────────────────────────────────────────────────────

def get_ai_summary(nifty_val: float, nifty_pct: float,
                   fii_net, dii_net,
                   sp500_chg: float, nasdaq_chg: float) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY missing — using fallback.")
        return "Market closed with mixed signals — watch the key support/resistance tomorrow."

    try:
        client = genai.Client(api_key=api_key)
        fii_str = f"FII net {fii_net:+,.0f} Cr" if fii_net is not None else "FII data unavailable"
        dii_str = f"DII net {dii_net:+,.0f} Cr" if dii_net is not None else "DII data unavailable"
        prompt = (
            f"Nifty 50 closed at {nifty_val:.2f} ({nifty_pct:+.2f}%). "
            f"{fii_str}, {dii_str}. "
            f"S&P 500 was {sp500_chg:+.2f}%, Nasdaq {nasdaq_chg:+.2f}% overnight. "
            "Write exactly ONE sharp, informal, tech-savvy sentence summarising today's market intelligence for traders."
        )
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return resp.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return "Market closed with mixed signals — watch the key support/resistance tomorrow."


# ─── REPORT GENERATOR ─────────────────────────────────────────────────────────

def generate_report() -> str:
    """
    Called by bot.py.
    Returns a Markdown-formatted string.
    The string contains 'Intelligence' for normal reports or 'Holiday' for off days.
    """
    today_name = datetime.now().strftime("%A")
    today_str  = datetime.now().strftime("%d %b %Y")

    if is_market_holiday():
        return (
            f"🏖️ *Market Holiday — {today_str}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"NSE is closed today. Enjoy the break!\n"
            f"Nivesh Niti resumes on the next trading day. 💎"
        )

    # Fetch all data
    nifty_val, nifty_pct = fetch_nifty()

    fii_net, dii_net = None, None
    for attempt in range(3):
        print(f"FII/DII attempt {attempt + 1}/3…")
        fii_net, dii_net = fetch_fii_dii()
        if fii_net is not None:
            break
        if attempt < 2:
            time.sleep(10)

    global_markets = fetch_global_markets()
    sp500_chg  = global_markets.get("S&P 500",   {}).get("change", 0.0)
    nasdaq_chg = global_markets.get("Nasdaq",    {}).get("change", 0.0)
    dow_chg    = global_markets.get("Dow Jones", {}).get("change", 0.0)
    sp500_val  = global_markets.get("S&P 500",   {}).get("value",  0.0)
    nasdaq_val = global_markets.get("Nasdaq",    {}).get("value",  0.0)
    dow_val    = global_markets.get("Dow Jones", {}).get("value",  0.0)

    advances, declines, unchanged = fetch_market_breadth()

    summary = get_ai_summary(nifty_val, nifty_pct, fii_net, dii_net, sp500_chg, nasdaq_chg)

    # Build report
    n_emoji = "📈" if nifty_pct >= 0 else "📉"
    s_emoji = "📈" if sp500_chg  >= 0 else "📉"
    q_emoji = "📈" if nasdaq_chg >= 0 else "📉"
    d_emoji = "📈" if dow_chg    >= 0 else "📉"

    report = (
        f"📊 *Nivesh Niti: Market Intelligence*\n"
        f"📅 {today_name}, {today_str}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🇮🇳 *Nifty 50:* {nifty_val:,.2f} ({nifty_pct:+.2f}%) {n_emoji}\n\n"
    )

    if fii_net is not None and dii_net is not None:
        fii_emoji = "🟢" if fii_net >= 0 else "🔴"
        dii_emoji = "🟢" if dii_net >= 0 else "🔴"
        report += (
            f"🏛️ *Institutional Activity (Net):*\n"
            f"• *FII:* ₹{fii_net:,.2f} Cr {fii_emoji}\n"
            f"• *DII:* ₹{dii_net:,.2f} Cr {dii_emoji}\n\n"
        )
    else:
        report += "⏳ *Institutional Data:* Not yet available from NSE.\n\n"

    if advances != "N/A":
        report += (
            f"📊 *Market Breadth (Nifty 50):*\n"
            f"🟢 Advances: {advances} | 🔴 Declines: {declines} | ⚪ Unchanged: {unchanged}\n\n"
        )

    report += (
        f"🌍 *Global Cues:*\n"
        f"• *S&P 500:* {sp500_val:,.2f} ({sp500_chg:+.2f}%) {s_emoji}\n"
        f"• *Nasdaq:* {nasdaq_val:,.2f} ({nasdaq_chg:+.2f}%) {q_emoji}\n"
        f"• *Dow Jones:* {dow_val:,.2f} ({dow_chg:+.2f}%) {d_emoji}\n\n"
        f"🤖 *AI Take:* {summary}\n\n"
        f"💎 *Premium:* Whale Watch report at 6:45 PM!"
    )

    return report
