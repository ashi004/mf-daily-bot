import requests
import yfinance as yf
import random
from datetime import datetime

# --- CONFIGURATION ---
WATCHLIST = [
    {"code": "120465", "name": "Axis Bluechip", "cat": "Large Cap"},
    {"code": "119706", "name": "SBI Bluechip", "cat": "Large Cap"},
    {"code": "118969", "name": "HDFC Mid-Cap", "cat": "Mid Cap"},
    {"code": "125354", "name": "Axis Midcap", "cat": "Mid Cap"},
    {"code": "118778", "name": "Nippon Small Cap", "cat": "Small Cap"},
    {"code": "119608", "name": "SBI Small Cap", "cat": "Small Cap"},
    {"code": "122639", "name": "Parag Parikh Flexi", "cat": "Flexi Cap"}
]

# Tickers for Indices, Sectors, and Commodities
TICKERS = {
    "indices": {
        "^NSEI": "NIFTY 50",
        "^BSESN": "SENSEX"
    },
    "sectors": {
        "^NSEBANK": "Bank",
        "^CNXIT": "IT",
        "^CNXAUTO": "Auto",
        "^CNXPHARMA": "Pharma",
        "^CNXMETAL": "Metal"
    },
    "commodities": {
        "GC=F": "Gold",
        "SI=F": "Silver"
    }
}

QUOTES = [
    "Price is what you pay. Value is what you get. – Warren Buffett",
    "The four most dangerous words in investing are: 'This time it's different.'",
    "Compound interest is the eighth wonder of the world.",
    "Be fearful when others are greedy and greedy when others are fearful."
]

def get_live_data(ticker_symbol):
    """Fetches simple change % for any ticker."""
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="2d")
        if len(hist) >= 2:
            today = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = ((today - prev) / prev) * 100
            return today, change
    except:
        return 0, 0

def get_market_summary():
    """Builds the Market, Sector, and Commodity section."""
    report = ""
    
    # 1. Main Indices
    report += "📊 *Market Pulse*\n"
    for sym, name in TICKERS["indices"].items():
        val, chg = get_live_data(sym)
        emoji = "🟢" if chg >= 0 else "🔴"
        report += f"{emoji} {name}: {val:,.0f} ({chg:+.2f}%)\n"
    
    # 2. Sector Watch (Find Best & Worst)
    sector_data = []
    for sym, name in TICKERS["sectors"].items():
        _, chg = get_live_data(sym)
        sector_data.append((name, chg))
    
    # Sort sectors
    sector_data.sort(key=lambda x: x[1], reverse=True)
    best_sector = sector_data[0]
    worst_sector = sector_data[-1]
    
    report += f"\n🏗 *Sector Watch*\n"
    report += f"🚀 Leader: *{best_sector[0]}* ({best_sector[1]:+.2f}%)\n"
    report += f"🐢 Laggard: *{worst_sector[0]}* ({worst_sector[1]:+.2f}%)\n"

    # 3. Commodities
    report += f"\n✨ *Commodities (Global)*\n"
    for sym, name in TICKERS["commodities"].items():
        val, chg = get_live_data(sym)
        emoji = "🔼" if chg >= 0 else "🔽"
        # Gold/Silver prices in USD usually, so we focus on % change
        report += f"{emoji} {name}: {chg:+.2f}%\n"

    return report

def get_fund_performance(scheme_code, days=1):
    """Calculates return for 1 Day OR 7 Days."""
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    try:
        response = requests.get(url)
        data = response.json()
        nav_data = data.get("data", [])
        if len(nav_data) > days:
            latest = float(nav_data[0]['nav'])
            past = float(nav_data[days]['nav'])
            ret = ((latest - past) / past) * 100
            return ret, nav_data[0]['date']
    except:
        pass
    return 0, None

def generate_report(report_type="daily"):
    lookback = 7 if report_type == "weekly" else 1
    
    # Header
    if report_type == "weekly":
        week_num = datetime.now().isocalendar()[1]
        header = f"🗓 *Weekly Wrap: Week {week_num}*"
    else:
        now_str = datetime.now().strftime("%d %b")
        header = f"📅 *Daily Update: {now_str}*"

    # PART 1: Market Data (Real-time)
    body = f"{header}\n━━━━━━━━━━━━━━━━━━\n"
    body += get_market_summary()
    body += "━━━━━━━━━━━━━━━━━━\n"

    # PART 2: Mutual Funds (NAV Data)
    mf_results = []
    latest_nav_date = ""
    for fund in WATCHLIST:
        ret, date = get_fund_performance(fund["code"], days=lookback)
        if date:
            mf_results.append({"name": fund["name"], "return": ret})
            latest_nav_date = date

    mf_results.sort(key=lambda x: x['return'], reverse=True)
    
    time_label = "Week" if report_type == "weekly" else "Day"
    body += f"🏆 *Top MF Gainers ({time_label})*\n"
    for f in mf_results[:3]:
        body += f"🟢 {f['name']}: *{f['return']:+.2f}%*\n"

    if report_type == "weekly":
         body += f"\n📉 *Top Losers*\n"
         for f in mf_results[-3:]:
            body += f"🔴 {f['name']}: *{f['return']:+.2f}%*\n"

    # PART 3: Footer
    body += "━━━━━━━━━━━━━━━━━━\n"
    body += f"🧠 _{random.choice(QUOTES)}_"
    
    return body