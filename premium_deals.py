"""
premium_deals.py
-----------------
Whale Watch report: fetches Bulk Deals and Insider Trading from NSE
using direct HTTP requests (no unstable third-party NSE libraries).
Sends a text summary + Excel file to the premium Telegram channel.
"""

import os
import time
import requests
import pandas as pd
import telebot
from io import BytesIO
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


def _get_nse_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(2)
        session.get("https://www.nseindia.com/market-data/bulk-block-deals", timeout=15)
        time.sleep(1)
    except Exception as e:
        print(f"NSE warm-up error: {e}")
    return session


# ─── DATA FETCHERS ────────────────────────────────────────────────────────────

def fetch_bulk_deals() -> pd.DataFrame:
    """Fetches bulk deals directly from NSE JSON API."""
    try:
        session = _get_nse_session()
        resp = session.get(
            "https://www.nseindia.com/api/bulk-deals-new",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # NSE returns {"data": [...]} or just [...]
        records = data.get("data", data) if isinstance(data, dict) else data
        if not records:
            print("Bulk deals: empty response")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        print(f"Bulk deals fetched: {len(df)} rows")
        return df

    except Exception as e:
        print(f"Bulk deals fetch error: {e}")
        return pd.DataFrame()


def fetch_insider_trading() -> pd.DataFrame:
    """Fetches insider trading data directly from NSE JSON API."""
    try:
        session = _get_nse_session()
        resp = session.get(
            "https://www.nseindia.com/api/corporates-pit?index=equities&period=oneDay",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("data", data) if isinstance(data, dict) else data
        if not records:
            print("Insider trading: empty response")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        print(f"Insider trading fetched: {len(df)} rows")
        return df

    except Exception as e:
        print(f"Insider trading fetch error: {e}")
        return pd.DataFrame()


# ─── EXCEL BUILDER ────────────────────────────────────────────────────────────

def build_excel(bulk_df: pd.DataFrame, insider_df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book

        header_fmt = wb.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        cell_fmt = wb.add_format({"border": 1})
        num_fmt  = wb.add_format({"border": 1, "num_format": "#,##0.00"})

        def write_sheet(df: pd.DataFrame, name: str):
            if df.empty:
                return
            df.to_excel(writer, sheet_name=name, index=False, startrow=1, header=False)
            ws = writer.sheets[name]
            for i, col in enumerate(df.columns):
                ws.write(0, i, col, header_fmt)
                width = max(len(str(col)), df[col].astype(str).map(len).max() if not df.empty else 0)
                ws.set_column(i, i, min(width + 4, 40))
            for r in range(len(df)):
                for c in range(len(df.columns)):
                    val = df.iloc[r, c]
                    fmt = num_fmt if isinstance(val, (int, float)) else cell_fmt
                    ws.write(r + 1, c, val, fmt)

        write_sheet(bulk_df,    "Bulk_Deals")
        write_sheet(insider_df, "Insider_Trading")

    output.seek(0)
    return output


# ─── SUMMARY MESSAGE ──────────────────────────────────────────────────────────

def _col(df: pd.DataFrame, *keywords) -> str | None:
    """Finds first column whose name contains any of the keywords (case-insensitive)."""
    for kw in keywords:
        for c in df.columns:
            if kw.lower() in c.lower():
                return c
    return None


def build_message(bulk_df: pd.DataFrame, insider_df: pd.DataFrame) -> str:
    msg = "🐋 *PREMIUM: Daily Whale Watch Report*\n━━━━━━━━━━━━━━━━━━\n\n"

    # ── Insider: Promoter buys ──
    if not insider_df.empty:
        cat_col  = _col(insider_df, "category", "person")
        mode_col = _col(insider_df, "mode", "acquisition", "transtype")
        sym_col  = _col(insider_df, "symbol")
        qty_col  = _col(insider_df, "qty", "quantity", "secqty", "no_")

        if cat_col and mode_col and sym_col:
            mask = (
                insider_df[cat_col].astype(str).str.upper().str.contains("PROMOTER", na=False) &
                insider_df[mode_col].astype(str).str.upper().str.contains("PURCHASE|BUY", na=False)
            )
            p_buys = insider_df[mask].head(5)
            if not p_buys.empty:
                msg += "🔑 *Promoter Market Buys (Top 5):*\n"
                for _, row in p_buys.iterrows():
                    qty = f"{int(float(row[qty_col])):,}" if qty_col else "N/A"
                    msg += f"• *{row[sym_col]}*: {qty} shares\n"
                msg += "\n"

    # ── Bulk Deals: buy side ──
    if not bulk_df.empty:
        side_col = _col(bulk_df, "buysell", "buy / sell", "side", "type")
        sym_col  = _col(bulk_df, "symbol")
        qty_col  = _col(bulk_df, "qty", "quantity")

        if side_col and sym_col:
            buys = bulk_df[
                bulk_df[side_col].astype(str).str.upper().str.contains("BUY", na=False)
            ].head(5)
            if not buys.empty:
                msg += "🏛️ *Top Bulk Buys (Top 5):*\n"
                for _, row in buys.iterrows():
                    qty = f"{int(float(row[qty_col])):,}" if qty_col else "N/A"
                    msg += f"• *{row[sym_col]}*: {qty} shares\n"
                msg += "\n"

    if not bulk_df.empty or not insider_df.empty:
        msg += "📑 *Full data attached* — open the Excel file for complete details."
    else:
        msg += (
            "⚠️ Could not fetch live NSE data today.\n"
            "Market may be closed or NSE API is temporarily down."
        )
    return msg


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run_whale_watch():
    token      = os.getenv("TELEGRAM_TOKEN")
    premium_id = os.getenv("PREMIUM_CHAT_ID")

    if not token or not premium_id:
        print("❌ TELEGRAM_TOKEN or PREMIUM_CHAT_ID missing.")
        return

    bot = telebot.TeleBot(token)

    print("📦 Fetching bulk deals...")
    bulk_df = fetch_bulk_deals()

    print("🔍 Fetching insider trading...")
    insider_df = fetch_insider_trading()

    msg = build_message(bulk_df, insider_df)
    bot.send_message(premium_id, msg, parse_mode="Markdown")

    if not bulk_df.empty or not insider_df.empty:
        excel = build_excel(bulk_df, insider_df)
        bot.send_document(
            premium_id,
            document=("NSE_Whale_Report.xlsx", excel),
            caption="📊 Nivesh Niti Premium: Bulk & Insider Data",
        )
        print("✅ Whale Watch report sent with Excel.")
    else:
        print("⚠️ No data — only text summary sent.")


if __name__ == "__main__":
    run_whale_watch()
