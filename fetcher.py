import requests
import yfinance as yf
import random

# --- 1. THE SMART POOL (Add your favorite funds here) ---
# The more you add, the better your "Top 3" analysis will be.
WATCHLIST = [
    # Large Cap
    {"code": "120465", "name": "Axis Bluechip", "cat": "Large Cap"},
    {"code": "119706", "name": "SBI Bluechip", "cat": "Large Cap"},
    {"code": "100355", "name": "Nippon India Large Cap", "cat": "Large Cap"},
    # Mid Cap
    {"code": "118969", "name": "HDFC Mid-Cap Opp", "cat": "Mid Cap"},
    {"code": "125354", "name": "Axis Midcap", "cat": "Mid Cap"},
    {"code": "120726", "name": "Kotak Emerging Equity", "cat": "Mid Cap"},
    # Small Cap
    {"code": "118778", "name": "Nippon Small Cap", "cat": "Small Cap"},
    {"code": "125497", "name": "Axis Small Cap", "cat": "Small Cap"},
    {"code": "119608", "name": "SBI Small Cap", "cat": "Small Cap"},
    # Flexi Cap
    {"code": "122639", "name": "Parag Parikh Flexi", "cat": "Flexi Cap"},
    {"code": "125350", "name": "Axis Flexi Cap", "cat": "Flexi Cap"}
]

FACTS = [
    "Did you know? The power of compounding is called the 8th wonder of the world.",
    "Fact: Missing just the 10 best days in the market can cut your returns by half.",
    "Tip: SIPs work best when the market is falling (Rupee Cost Averaging).",
    "Rule of 72: Divide 72 by your return rate to see how many years to double money.",
    "Fact: Mutual Funds are subject to market risks, but inflation is a guaranteed loss."
]

def get_market_status():
    """Fetches real-time NIFTY 50 Index data."""
    try:
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="5d") # Get last 5 days
        if len(hist) >= 2:
            today_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = ((today_close - prev_close) / prev_close) * 100
            
            emoji = "🟢" if change >= 0 else "🔴"
            return f"{emoji} *NIFTY 50 Live:* {today_close:.0f} ({change:+.2f}%)"
    except Exception as e:
        return "⚠️ Nifty Data Unavailable"
    return "⚠️ Nifty Data Unavailable"

def get_nav_return(scheme_code):
    """Calculates 1-Day Return for a fund."""
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    try:
        response = requests.get(url)
        data = response.json()
        nav_data = data.get("data", [])
        
        if len(nav_data) >= 2:
            latest_nav = float(nav_data[0]['nav'])
            prev_nav = float(nav_data[1]['nav'])
            date = nav_data[0]['date']
            
            # Calculate Return
            ret = ((latest_nav - prev_nav) / prev_nav) * 100
            return latest_nav, ret, date
    except:
        pass
    return 0, 0, None

def generate_smart_report():
    """Generates the full ranking report."""
    
    # 1. Fetch Data for ALL funds in pool
    results = []
    latest_date = ""
    
    for fund in WATCHLIST:
        nav, ret, date = get_nav_return(fund["code"])
        if nav > 0:
            results.append({
                "name": fund["name"],
                "cat": fund["cat"],
                "return": ret,
                "nav": nav
            })
            latest_date = date

    # 2. Sort by Return (High to Low)
    results.sort(key=lambda x: x['return'], reverse=True)
    
    # 3. Pick Winners (Top 3) & Losers (Bottom 3)
    top_3 = results[:3]
    bottom_3 = results[-3:]
    
    # 4. Build the Report Text
    report = f"📅 *NAV Update: {latest_date}*\n\n"
    
    # Add Market Context
    report += f"{get_market_status()}\n"
    report += "━━━━━━━━━━━━━━━━━━\n"
    
    # Top Gainers Section
    report += "\n🏆 *Top 3 Gainers (1-Day)*\n"
    for f in top_3:
        report += f"🟢 {f['name']}: *{f['return']:+.2f}%*\n"
        
    # Top Losers Section
    report += "\n📉 *Top 3 Losers (1-Day)*\n"
    for f in bottom_3:
        report += f"🔴 {f['name']}: *{f['return']:+.2f}%*\n"
        
    # Add Random Fact
    report += "\n━━━━━━━━━━━━━━━━━━\n"
    report += f"🧠 _{random.choice(FACTS)}_"
    
    return report