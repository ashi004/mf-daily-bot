def generate_report():
    # ... Holiday Check and Header ...

    # 1. Market Overview (Nifty 50, Sensex, Nifty 500)
    body += "🌐 *Market Overview*\n"
    idx_summary = ""
    for sym, name in TICKERS["indices"].items():
        val, chg = get_live_data(sym)
        if val: 
            body += f"{'🟢' if chg >= 0 else '🔴'} {name}: {chg:+.2f}%\n"
            idx_summary += f"{name} {chg:+.2f}% "

    # 2. Sectoral Leaderboard (Strict 2 Leader / 2 Laggard Limit)
    sector_results = []
    for sym, name in TICKERS["sectors"].items():
        _, chg = get_live_data(sym)
        if chg is not None: sector_results.append((name, chg))
    
    sector_results.sort(key=lambda x: x[1], reverse=True)
    
    body += f"\n🚀 *Sectoral Leaders*\n"
    for name, chg in sector_results[:2]: # Top 2 Only
        body += f"• {name}: *{chg:+.2f}%*\n"
        
    body += f"\n🐢 *Sectoral Laggards*\n"
    for name, chg in sector_results[-2:]: # Bottom 2 Only
        body += f"• {name}: *{chg:+.2f}%*\n"

    # 3. Commodities
    body += f"\n✨ *Commodities*\n"
    for sym, name in TICKERS["commodities"].items():
        _, chg = get_live_data(sym)
        if chg is not None: body += f"{'🔼' if chg >= 0 else '🔽'} {name}: {chg:+.2f}%\n"

    # 4. Momentum Discovery (2 Most Positive, 2 Most Negative)
    body += "━━━━━━━━━━━━━━━━━━\n🏆 *Momentum Discovery (Today)*\n"
    # We increase the scan sample to 200 to find enough negative movers on green days
    all_funds = get_unlimited_discovery(sample_size=200) 
    all_funds.sort(key=lambda x: x['chg'], reverse=True)

    body += "📈 *Top Gainers*\n"
    for f in all_funds[:2]:
        body += f"⚡ {f['name']}: *{f['chg']:+.2f}%*\n"

    body += "\n📉 *Top Drifters*\n"
    for f in all_funds[-2:]:
        body += f"❄️ {f['name']}: *{f['chg']:+.2f}%*\n"

    # 5. Stealth Insight
    body += "━━━━━━━━━━━━━━━━━━\n💡 *Expert View:* \n_" + get_stealth_insight(idx_summary) + "_"
    
    return body