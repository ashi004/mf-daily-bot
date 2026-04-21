"""
premium_xray.py
---------------
Weekend Portfolio X-Ray report.
Fetches mutual fund holdings via mftool and calculates portfolio overlap
between popular fund pairs to flag redundancy for subscribers.
"""

import os
import time
import telebot
from mftool import Mftool
from dotenv import load_dotenv

load_dotenv()

mf = Mftool()

# ─── POPULAR FUND PAIRS TO COMPARE ────────────────────────────────────────────
# Format: (Fund A name, Fund A scheme code, Fund B name, Fund B scheme code)
FUND_PAIRS = [
    ("Parag Parikh Flexi Cap",  "122639", "HDFC Top 100",          "118989"),
    ("Mirae Asset Large Cap",   "118825", "Axis Bluechip",          "120465"),
    ("SBI Small Cap",           "125497", "Nippon India Small Cap", "118778"),
    ("Canara Rob Flexi Cap",    "120586", "UTI Flexi Cap",          "120716"),
]

# ─── OVERLAP LOGIC ────────────────────────────────────────────────────────────

def get_holdings(scheme_code: str) -> set:
    """
    Tries to get the top-holding stock names for a scheme.
    mftool.get_scheme_portfolio_data() returns a dict with a 'holdings' key.
    Falls back gracefully to empty set on any error.
    """
    try:
        data = mf.get_scheme_portfolio_data(scheme_code)
        if not data or "holdings" not in data:
            print(f"No portfolio data for {scheme_code}")
            return set()
        holdings = data["holdings"]
        # Each holding is a dict; the stock name is usually under 'stock_name' or 'stkName'
        names = set()
        for h in holdings:
            name = (
                h.get("stock_name")
                or h.get("stkName")
                or h.get("name")
                or ""
            )
            if name.strip():
                names.add(name.strip().upper())
        print(f"Scheme {scheme_code} → {len(names)} stocks")
        return names
    except Exception as e:
        print(f"Holdings fetch error for {scheme_code}: {e}")
        return set()


def jaccard_overlap(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union        = len(set_a | set_b)
    return (intersection / union) * 100 if union > 0 else 0.0


def overlap_verdict(pct: float) -> str:
    if pct >= 60:
        return "🔴 *Very High Overlap* — You're essentially holding the same portfolio twice."
    if pct >= 40:
        return "🟡 *Moderate Overlap* — Some redundancy; review if both funds are needed."
    if pct >= 20:
        return "🟢 *Low Overlap* — Good diversification across these two strategies."
    return "🟢 *Minimal Overlap* — These funds complement each other well."


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run_xray_report():
    token      = os.getenv("TELEGRAM_TOKEN")
    premium_id = os.getenv("PREMIUM_CHAT_ID")

    if not token or not premium_id:
        print("❌ TELEGRAM_TOKEN or PREMIUM_CHAT_ID missing.")
        return

    bot = telebot.TeleBot(token)

    message = (
        "🧐 *Premium Weekend X-Ray: Portfolio Overlap Analysis*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "_Are you actually diversified? Here's what the data says:_\n\n"
    )

    any_data = False

    for name_a, code_a, name_b, code_b in FUND_PAIRS:
        print(f"Comparing {name_a} vs {name_b}…")
        holdings_a = get_holdings(code_a)
        time.sleep(1)
        holdings_b = get_holdings(code_b)

        if not holdings_a or not holdings_b:
            message += (
                f"📊 *{name_a}* vs *{name_b}*\n"
                f"⚠️ Could not fetch holdings data.\n\n"
            )
            continue

        overlap = jaccard_overlap(holdings_a, holdings_b)
        common  = sorted(holdings_a & holdings_b)[:5]  # top 5 common stocks

        any_data = True
        message += (
            f"📊 *{name_a}* vs *{name_b}*\n"
            f"⚠️ Overlap Score: *{overlap:.1f}%*\n"
            f"💡 {overlap_verdict(overlap)}\n"
        )
        if common:
            message += f"🔀 Common holdings (sample): {', '.join(common)}\n"
        message += "\n"

    if not any_data:
        message += (
            "⚠️ Could not fetch live fund data from mftool today.\n"
            "This can happen on weekends when AMFI data is being refreshed.\n"
            "Try again next Saturday!"
        )

    message += "_Data sourced from AMFI via mftool. Updated monthly._"

    bot.send_message(premium_id, message, parse_mode="Markdown")
    print("✅ X-Ray report sent.")


if __name__ == "__main__":
    run_xray_report()
