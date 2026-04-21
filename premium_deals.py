import os
import time
import pandas as pd
import telebot
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# ─── DATA FETCHING ────────────────────────────────────────────────────────────

def fetch_bulk_deals() -> pd.DataFrame:
    """Fetch bulk deals from NSE. Tries NseKit first, then nselib."""
    # Method 1: NseKit
    try:
        from NseKit import get
        df = get.bulk_deals()
        if df is not None and not df.empty:
            print(f"[BulkDeals] NseKit → {len(df)} rows")
            return df
    except Exception as e:
        print(f"[BulkDeals] NseKit failed: {e}")

    # Method 2: nselib
    try:
        from nselib import capital_market
        df = capital_market.bulk_deal_data()
        if df is not None and not df.empty:
            print(f"[BulkDeals] nselib → {len(df)} rows")
            return df
    except Exception as e:
        print(f"[BulkDeals] nselib failed: {e}")

    return pd.DataFrame()


def fetch_insider_trading() -> pd.DataFrame:
    """Fetch insider trading data. Tries nselib first, then NseKit."""
    # Method 1: nselib
    try:
        from nselib import capital_market
        df = capital_market.insider_trading_data(period='1D')
        if df is not None and not df.empty:
            print(f"[Insider] nselib → {len(df)} rows")
            return df
    except Exception as e:
        print(f"[Insider] nselib failed: {e}")

    # Method 2: NseKit
    try:
        from NseKit import get
        df = get.insider_trading()
        if df is not None and not df.empty:
            print(f"[Insider] NseKit → {len(df)} rows")
            return df
    except Exception as e:
        print(f"[Insider] NseKit failed: {e}")

    return pd.DataFrame()


# ─── EXCEL BUILDER ───────────────────────────────────────────────────────────

def build_excel(bulk_df: pd.DataFrame, insider_df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1F4E79', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        cell_fmt = workbook.add_format({'border': 1})

        def write_sheet(df: pd.DataFrame, sheet_name: str):
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)
            ws = writer.sheets[sheet_name]
            for col_num, col_name in enumerate(df.columns):
                ws.write(0, col_num, col_name, header_fmt)
                # Auto-fit column width
                max_len = max(len(str(col_name)), df[col_name].astype(str).map(len).max() if not df.empty else 0)
                ws.set_column(col_num, col_num, min(max_len + 4, 40))
            for row_num in range(len(df)):
                for col_num in range(len(df.columns)):
                    val = df.iloc[row_num, col_num]
                    if isinstance(val, (int, float)):
                        ws.write(row_num + 1, col_num, val, num_fmt)
                    else:
                        ws.write(row_num + 1, col_num, str(val), cell_fmt)

        if not bulk_df.empty:
            write_sheet(bulk_df, 'Bulk_Deals')
        if not insider_df.empty:
            write_sheet(insider_df, 'Insider_Trading')

    output.seek(0)
    return output


# ─── MESSAGE BUILDER ─────────────────────────────────────────────────────────

def build_summary_message(bulk_df: pd.DataFrame, insider_df: pd.DataFrame) -> str:
    message = "🐋 *PREMIUM: Daily Whale Watch Report*\n━━━━━━━━━━━━━━━━━━\n"

    # Insider – Promoter buys
    if not insider_df.empty:
        # Try to identify promoter buys (column names vary by source)
        cat_col = next((c for c in insider_df.columns if 'category' in c.lower() or 'person' in c.lower()), None)
        mode_col = next((c for c in insider_df.columns if 'mode' in c.lower() or 'acquisition' in c.lower()), None)
        sym_col  = next((c for c in insider_df.columns if 'symbol' in c.lower()), None)
        qty_col  = next((c for c in insider_df.columns if 'qty' in c.lower() or 'no_' in c.lower() or 'quantity' in c.lower()), None)

        if cat_col and mode_col and sym_col:
            mask = (
                insider_df[cat_col].str.upper().str.contains('PROMOTER', na=False) &
                insider_df[mode_col].str.upper().str.contains('PURCHASE|BUY', na=False)
            )
            p_buys = insider_df[mask].head(5)
            if not p_buys.empty:
                message += "🔑 *Promoter Market Buys (Top 5):*\n"
                for _, row in p_buys.iterrows():
                    qty = f"{int(row[qty_col]):,}" if qty_col else "N/A"
                    message += f"• *{row[sym_col]}*: {qty} shares\n"
                message += "\n"

    # Bulk Deals – buy side
    if not bulk_df.empty:
        buy_col = next((c for c in bulk_df.columns if 'buy' in c.lower() and 'sell' in c.lower()), None)
        if buy_col is None:
            buy_col = next((c for c in bulk_df.columns if 'buy' in c.lower() or 'side' in c.lower()), None)
        sym_col = next((c for c in bulk_df.columns if 'symbol' in c.lower()), None)
        qty_col = next((c for c in bulk_df.columns if 'qty' in c.lower() or 'quantity' in c.lower()), None)

        if buy_col and sym_col:
            b_buys = bulk_df[bulk_df[buy_col].str.upper().str.contains('BUY', na=False)].head(5)
            if not b_buys.empty:
                message += "🏛️ *Top Bulk Buys (Top 5):*\n"
                for _, row in b_buys.iterrows():
                    qty = f"{int(row[qty_col]):,}" if qty_col else "N/A"
                    message += f"• *{row[sym_col]}*: {qty} shares\n"
                message += "\n"

    if not bulk_df.empty or not insider_df.empty:
        message += "📑 *Full Data Attached:* Open the Excel file for the complete list."
    else:
        message += "⚠️ *Note:* Could not fetch live data from NSE today. Market may be closed or NSE API is down."

    return message


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run_whale_watch():
    token      = os.getenv("TELEGRAM_TOKEN")
    premium_id = os.getenv("PREMIUM_CHAT_ID")

    if not token or not premium_id:
        print("❌ TELEGRAM_TOKEN or PREMIUM_CHAT_ID missing.")
        return

    bot = telebot.TeleBot(token)

    print("📦 Fetching bulk deals…")
    bulk_df = fetch_bulk_deals()

    print("🔍 Fetching insider trading…")
    insider_df = fetch_insider_trading()

    message = build_summary_message(bulk_df, insider_df)

    # Always send text summary
    bot.send_message(premium_id, message, parse_mode="Markdown")

    # Send Excel only if we have data
    if not bulk_df.empty or not insider_df.empty:
        excel_bytes = build_excel(bulk_df, insider_df)
        bot.send_document(
            premium_id,
            document=('NSE_Whale_Report.xlsx', excel_bytes),
            caption="📊 Nivesh Niti Premium: Bulk & Insider Data"
        )
        print("✅ Whale Watch report sent with Excel attachment.")
    else:
        print("⚠️ No data to attach — only text summary sent.")


if __name__ == "__main__":
    run_whale_watch()
